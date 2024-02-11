#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from decimal import Decimal

from ikabot.config import materials_names
from ikabot.helpers.citiesAndIslands import chooseCity, getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, daysHoursMinutes, enter
from ikabot.helpers.resources import getProductionPerSecond
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def getStatus(ikariam_service: IkariamService, db: Database, telegram: Telegram):

    banner()

    (ids, __) = getIdsOfCities(ikariam_service)
    total_resources = [0] * len(materials_names)
    total_production = [0] * len(materials_names)
    total_wine_consumption = 0
    housing_space = 0
    citizens = 0
    total_housing_space = 0
    total_citizens = 0
    available_ships = 0
    total_ships = 0
    for id in ids:
        ikariam_service.get('view=city&cityId={}'.format(id), noIndex=True)
        data = ikariam_service.get('view=updateGlobalData&ajax=1', noIndex=True)
        json_data = json.loads(data, strict=False)
        json_data = json_data[0][1]['headerData']
        if json_data['relatedCity']['owncity'] != 1:
            continue
        wood = Decimal(json_data['resourceProduction'])
        good = Decimal(json_data['tradegoodProduction'])
        typeGood = int(json_data['producedTradegood'])
        total_production[0] += wood * 3600
        total_production[typeGood] += good * 3600
        total_wine_consumption += json_data['wineSpendings']
        housing_space = int(json_data['currentResources']['population'])
        citizens = int(json_data['currentResources']['citizens'])
        total_housing_space += housing_space
        total_citizens += citizens
        total_resources[0] += json_data['currentResources']['resource']
        total_resources[1] += json_data['currentResources']['1']
        total_resources[2] += json_data['currentResources']['2']
        total_resources[3] += json_data['currentResources']['3']
        total_resources[4] += json_data['currentResources']['4']
        available_ships = json_data['freeTransporters']
        total_ships = json_data['maxTransporters']
        total_gold = int(Decimal(json_data['gold']))
        total_gold_production = int(Decimal(json_data['scientistsUpkeep'] + json_data['income'] + json_data['upkeep']))
    print('Ships {:d}/{:d}'.format(int(available_ships), int(total_ships)))
    print('\nTotal:')
    print('{:>10}'.format(' '), end='|')
    for i in range(len(materials_names)):
        print('{:>12}'.format(materials_names[i]), end='|')
    print()
    print('{:>10}'.format('Available'), end='|')
    for i in range(len(materials_names)):
        print('{:>12}'.format(addThousandSeparator(total_resources[i])), end='|')
    print()
    print('{:>10}'.format('Production'), end='|')
    for i in range(len(materials_names)):
        print('{:>12}'.format(addThousandSeparator(total_production[i])), end='|')
    print()
    print('Housing Space: {}, Citizens: {}'.format(addThousandSeparator(total_housing_space), addThousandSeparator(citizens)))
    print('Gold: {}, Gold production: {}'.format(addThousandSeparator(total_gold), addThousandSeparator(total_gold_production)))
    print('Wine consumption: {}'.format(addThousandSeparator(total_wine_consumption)), end='')

    print('\nOf which city do you want to see the state?')
    city = chooseCity(ikariam_service)
    banner()

    (wood, good, typeGood) = getProductionPerSecond(ikariam_service, city['id'])
    print('{}{}{}{}'.format(Colours.Text.Format.BOLD, Colours.MATERIALS[int(typeGood)], city['cityName'], Colours.Text.RESET))

    resources = city['availableResources']
    storageCapacity = city['storageCapacity']
    colour_resources = []
    for i in range(len(materials_names)):
        if resources[i] == storageCapacity:
            colour_resources.append(Colours.Text.Light.RED)
        else:
            colour_resources.append(Colours.Text.RESET)
    print('Population:')
    print('{}: {} {}: {}'.format('Housing space', addThousandSeparator(housing_space), 'Citizens', addThousandSeparator(citizens)))
    print('Storage: {}'.format(addThousandSeparator(storageCapacity)))
    print('Resources:')
    for i in range(len(materials_names)):
        print('{} {}{}{} '.format(materials_names[i], colour_resources[i], addThousandSeparator(resources[i]), Colours.Text.RESET), end='')
    print('')

    print('Production:')
    print('{}: {} {}: {}'.format(materials_names[0], addThousandSeparator(wood*3600), materials_names[typeGood], addThousandSeparator(good*3600)))

    hasTavern = 'tavern' in [building['building'] for building in city['position']]
    if hasTavern:
        consumption_per_hour = city['wineConsumptionPerHour']
        if consumption_per_hour == 0:
            print('{}{}Does not consume wine!{}'.format(Colours.Text.Light.RED, Colours.Text.Format.BOLD, Colours.Text.RESET))
        else:
            if typeGood == 1 and (good*3600) > consumption_per_hour:
                elapsed_time_run_out = '∞'
            else:
                consumption_per_second = Decimal(consumption_per_hour) / Decimal(3600)
                remaining_resources_to_consume = Decimal(resources[1]) / Decimal(consumption_per_second)
                elapsed_time_run_out = daysHoursMinutes(remaining_resources_to_consume)
            print('There is wine for: {}'.format(elapsed_time_run_out))

    for building in [building for building in city['position'] if building['name'] != 'empty']:
        if building['isMaxLevel'] is True:
            colour = Colours.Text.Light.BLACK
        elif building['canUpgrade'] is True:
            colour = Colours.Text.Light.GREEN
        else:
            colour = Colours.Text.Light.RED

        level = building['level']
        if level < 10:
            level = ' ' + str(level)
        else:
            level = str(level)
        if building['isBusy'] is True:
            level = level + '+'

        print('lv:{}\t{}{}{}'.format(level, colour, building['name'], Colours.Text.RESET))

    enter()
