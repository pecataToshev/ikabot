#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import json

from ikabot.bot.trainArmyBot import TrainArmyBot
from ikabot.config import actionRequest, city_url, materials_names
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, daysHoursMinutes, enter
from ikabot.helpers.citiesAndIslands import chooseCity, getIdsOfCities
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def get_target_building(city: dict, building_type: str):
    for building in city['position']:
        if building['building'] == building_type:
            return building
    return None


def get_building_info(ikariam_service:IkariamService, city_id: int, building: dict):
    data = ikariam_service.post(
        params={
            'view': building['building'],
            'cityId': city_id,
            'position': building['position'],
            'backgroundView': 'city',
            'currentCityId': city_id,
            'actionRequest': actionRequest,
            'ajax': '1'
        }
    )
    return json.loads(data, strict=False)


def generateArmyData(units_info: dict) -> list[dict]:
    i = 1
    units = []
    while 'js_barracksSlider{:d}'.format(i) in units_info:
        # {'identifier':'phalanx','unit_type_id':303,'costs':{'citizens':1,'wood':27,'sulfur':30,'upkeep':3,'completiontime':71.169695412658},'local_name':'Hoplita'}
        info = units_info['js_barracksSlider{:d}'.format(i)]['slider']['control_data']
        info = json.loads(info, strict=False)
        units.append(info)
        i += 1
    return units


def __filter_cities_by_resource(cities, resource_id) -> dict[int,bool]:
    d = {}
    for _, city in cities.items():
        if city['tradegood'] == resource_id:
            d[city['id']] = True
    return d


def __define_trainings(units_info, train_troops: bool):
    units_src = generateArmyData(units_info)
    max_unit_name = max([len(unit['local_name']) for unit in units_src])
    trainings = []
    while True:
        units = copy.deepcopy(units_src)
        print('Train:')
        for unit in units:
            amount = read(msg='{: >{len}}:'.format(unit['local_name'], len=max_unit_name), min=0, empty=True)
            if amount == '':
                amount = 0
            unit['cantidad'] = amount

        # calculate costs
        cost = [0] * (len(materials_names) + 3)
        for unit in units:
            for i in range(len(materials_names)):
                material_name = materials_names[i].lower()
                if material_name in unit['costs']:
                    cost[i] += unit['costs'][material_name] * unit['cantidad']

            if 'citizens' in unit['costs']:
                cost[len(materials_names)+0] += unit['costs']['citizens'] * unit['cantidad']
            if 'upkeep' in unit['costs']:
                cost[len(materials_names)+1] += unit['costs']['upkeep'] * unit['cantidad']
            if 'completiontime' in unit['costs']:
                cost[len(materials_names)+2] += unit['costs']['completiontime'] * unit['cantidad']

        print('\nTotal cost:')
        for i in range(len(materials_names)):
            if cost[i] > 0:
                print('{}: {}'.format(materials_names[i], addThousandSeparator(cost[i])))
        if cost[len(materials_names)+0] > 0:
            print('Citizens: {}'.format(addThousandSeparator(cost[len(materials_names)+0])))
        if cost[len(materials_names)+1] > 0:
            print('Maintenance: {}'.format(addThousandSeparator(cost[len(materials_names)+1])))
        if cost[len(materials_names)+2] > 0:
            print('Duration: {}'.format(daysHoursMinutes(int(cost[len(materials_names)+2]))))

        if not askUserYesNo('Proceed'):
            break

        trainings.append(units)

        if not askUserYesNo('Do you want to train more {}'.format('troops' if train_troops else 'fleet')):
            break

    return trainings


def __get_cities_to_train(ikariam_service, city) -> dict:
    added_cities = {city['id']: True}
    if askUserYesNo('Do you want to replicate the training to other cities'):
        ids, cities = getIdsOfCities(ikariam_service)

        print('(0) Back')
        print('(1) All the wine cities')
        print('(2) All the marble cities')
        print('(3) All the cristal cities')
        print('(4) All the sulfur cities')
        print('(5) Choose City')
        print('(6) All City')

        selected = read(min=0, max=6, digit=True)
        if selected in [1, 2, 3, 4]:
            added_cities.update(__filter_cities_by_resource(cities, selected))
        elif selected == 5:
            while True:
                city = chooseCity(ikariam_service)
                if added_cities.get(city['id'], False):
                    print('\nYou have already selected this city!')
                    continue
                added_cities[city['id']] = True
                if not askUserYesNo('Do you want to add another city'):
                    break
        elif selected == 6:
            for city_id in ids:
                added_cities[city_id] = True

    return added_cities


def train_army_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    print('Do you want to train troops (1) or ships (2)?')
    rta = read(min=1, max=2)
    train_troops = rta == 1

    print('In what city do you want to train the {}?'.format('troops' if train_troops else 'fleet'))
    city = chooseCity(ikariam_service)
    banner()

    building_type = 'barracks' if train_troops else 'shipyard'
    building = get_target_building(city, building_type)
    if building is None:
        print(building_type, 'not built.')
        enter()
        return

    data = get_building_info(ikariam_service, city, building)
    trainings = __define_trainings(data[2][1], train_troops)
    training_cities_map = __get_cities_to_train(ikariam_service, city)
    for city_id in dict(training_cities_map):
        city = getCity(ikariam_service.get(city_url + str(city_id)))
        training_cities_map[city_id] = city

        building = get_target_building(city, building_type)
        if building is None:
            print('Cannot replicate trainings in', city['name'], 'due to', building_type, 'not built')
            training_cities_map.pop(city_id)
            continue

        # calculate if the city has enough resources
        resources_available = city['availableResources'].copy()
        resources_available.append(city['freeCitizens'])

        for training in trainings:
            for unit in training:
                if unit['cantidad'] != 0:
                    for i in range(len(materials_names)):
                        material_name = materials_names[i].lower()
                        if material_name in unit['costs']:
                            resources_available[i] -= (
                                unit['costs'][material_name] * unit['cantidad']
                            )

                    if 'citizens' in unit['costs']:
                        resources_available[len(materials_names)] -= (
                            unit['costs']['citizens'] * unit['cantidad']
                        )

        if len([elem for elem in resources_available if elem < 0]) > 0:
            print('\nThere are not enough resources in {}:'.format(city['name']))
            for i in range(len(materials_names)):
                if resources_available[i] < 0:
                    print(
                        '{}:{}'.format(
                            materials_names[i],
                            addThousandSeparator(resources_available[i] * -1),
                        )
                    )

            if resources_available[len(materials_names)] < 0:
                print(
                    'Citizens:{}'.format(
                        addThousandSeparator(
                            resources_available[len(materials_names)] * -1
                        )
                    )
                )

            if not askUserYesNo('Proceed anyway in {}'.format(city['name'])):
                training_cities_map.pop(city_id)
                continue

    if not askUserYesNo('Start trainings'):
        return

    for city in training_cities_map.values():
        TrainArmyBot(
            ikariam_service=ikariam_service,
            bot_config={
                'trainTroops': train_troops,
                'cityId': city['id'],
                'cityName': city['name'],
            },
        ).start(
            action='Train ' + ('troops' if train_troops else 'fleet'),
            objective='Execute {} trainings'.format(len(trainings)),
            target_city=city['name']
        )
        print('Started training {} in {}.'.format(('troops' if train_troops else 'fleet'), city['name']))
