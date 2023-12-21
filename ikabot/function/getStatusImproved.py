#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import gettext
from dataclasses import dataclass
from decimal import *
from ikabot.config import *
from ikabot.helpers.gui import *
from ikabot.helpers.naval import *
from ikabot.helpers.varios import *
from ikabot.helpers.resources import *
from ikabot.helpers.pedirInfo import *
from ikabot.helpers.getJson import getCity
from ikabot.helpers.market import printGoldForAllCities

t = gettext.translation('getStatus', localedir, languages=languages, fallback=True)
_ = t.gettext

getcontext().prec = 30

SECONDS_IN_HOUR = 3600
COLUMN_MAX_LENGTH = 25



def getStatusImproved(session, event, stdin_fd, predetermined_input):
    '''
    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    '''
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    try:
        banner()
        color_arr = [bcolors.ENDC, bcolors.HEADER, bcolors.STONE, bcolors.BLUE, bcolors.WARNING]

        [city_ids, _] = getIdsOfCities(session, False)

        total_resources = [0] * len(materials_names)
        total_production = [0] * len(materials_names)
        total_wine_consumption = 0
        housing_space = 0
        citizens = 0
        total_housing_space = 0
        total_citizens = 0
        available_ships = 0
        total_ships = 0

        print("gold for city {}".format(city_ids[0]))
        printGoldForAllCities(session, city_ids[0])
        print("ok?")

        for city_id in city_ids:


            print("\n\n=================================\nCity ID: {}\n".format(city_id))
            html = session.get(city_url + city_id)


            city = getCity(html)
            resource_production = getProductionPerSecond(session, city_id)
            resource_production_per_second = [int(resource_production[0] * SECONDS_IN_HOUR), 0, 0, 0, 0]
            resource_production_per_second[int(resource_production[2])] = int(resource_production[1] * SECONDS_IN_HOUR)
            city['resourceProductionPerHour'] = resource_production_per_second


            # print(getCity(session.get('view=city&cityId={}'.format(cityId), noIndex=True)))

            data = session.get('view=updateGlobalData&ajax=1', noIndex=True)
            json_data = json.loads(data, strict=False)
            # print("\n\n\ndata\n")
            # print(data)
            # print("\n\n\n\n")

            print(city)

            json_data = json_data[0][1]['headerData']
            if json_data['relatedCity']['owncity'] != 1:
                continue
            # print(json_data)
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

        print("\n\n\n\n\n\n\n\n")
        print(_('Ships {:d}/{:d}').format(int(available_ships), int(total_ships)))
        print(_('\nTotal:'))
        print('{:>10}'.format(' '), end='|')
        for i in range(len(materials_names)):
            print('{:>12}'.format(materials_names_english[i]), end='|')
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


































        print(_('\nOf which city do you want to see the state?'))
        city = chooseCity(session)
        banner()

        (wood, good, typeGood) = getProductionPerSecond(session, city['id'])
        print('\033[1m{}{}{}'.format(color_arr[int(typeGood)], city['cityName'], color_arr[0]))

        resources = city['availableResources']
        storageCapacity = city['storageCapacity']
        color_resources = []
        for i in range(len(materials_names)):
            if resources[i] == storageCapacity:
                color_resources.append(bcolors.RED)
            else:
                color_resources.append(bcolors.ENDC)
        print(_('Population:'))
        print('{}: {} {}: {}'.format('Housing space', addThousandSeparator(housing_space), 'Citizens', addThousandSeparator(citizens)))
        print(_('Storage: {}'.format(addThousandSeparator(storageCapacity))))
        print(_('Resources:'))
        for i in range(len(materials_names)):
            print('{} {}{}{} '.format(materials_names[i], color_resources[i], addThousandSeparator(resources[i]), bcolors.ENDC), end='')
        print('')

        print(_('Production:'))
        print('{}: {} {}: {}'.format(materials_names[0], addThousandSeparator(wood*3600), materials_names[typeGood], addThousandSeparator(good*3600)))

        hasTavern = 'tavern' in [building['building'] for building in city['position']]
        if hasTavern:
            consumption_per_hour = city['wineConsumption']
            if consumption_per_hour == 0:
                print(_('{}{}Does not consume wine!{}').format(bcolors.RED, bcolors.BOLD, bcolors.ENDC))
            else:
                if typeGood == 1 and (good*3600) > consumption_per_hour:
                    elapsed_time_run_out = '∞'
                else:
                    consumption_per_second = Decimal(consumption_per_hour) / Decimal(3600)
                    remaining_resources_to_consume = Decimal(resources[1]) / Decimal(consumption_per_second)
                    elapsed_time_run_out = daysHoursMinutes(remaining_resources_to_consume)
                print(_('There is wine for: {}').format(elapsed_time_run_out))
        
        for building in [building for building in city['position'] if building['name'] != 'empty']:
            if building['isMaxLevel'] is True:
                color = bcolors.BLACK
            elif building['canUpgrade'] is True:
                color = bcolors.GREEN
            else:
                color = bcolors.RED

            level = building['level']
            if level < 10:
                level = ' ' + str(level)
            else:
                level = str(level)
            if building['isBusy'] is True:
                level = level + '+'

            print(_('lv:{}\t{}{}{}').format(level, color, building['name'], bcolors.ENDC))

        enter()
        print('')
        event.set()
    except KeyboardInterrupt:
        event.set()
        return
