#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

from ikabot import config
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, daysHoursMinutes, enter, printProgressBar, \
    rightAlign
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


def get_number(s):
    return int(s.replace(',', '').replace('.', ''))

def _get_int(s: str) -> int:
    return int(str(s).replace(',', '').replace('.', ''))


def islandWorkplaces(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    action_exit = "Exit"
    action_donate = "Donate"
    action_change_workers = "Change workers"
    actions = [
        action_exit,
        action_donate,
        action_change_workers,
    ]

    # region Config
    column_separator = ' | '
    columns = [
        'Id',
        'City',
        'City Stats',
        'Resource',
        'Production',
        'Workers',
        'Overcharged',
        'level',
        'Upgrade wood required',
        'Free Upgrade Wood'
    ]
    column_length = [3, config.MAXIMUM_CITY_NAME_LENGTH, 17, 8, 10, 13, 11, 5, 23, 20]
    
    def get_view(material_ind):
        return 'resource' if material_ind == 0 else 'tradegood'

    def extract_workplace_data(init_data, material_ind, json):
        """
        Extracts workplace data from json
        :param init_data: dict with basic city data
        :param material_ind: int
        :param json: json data
        :return: workplace json
        """
        view = get_view(material_ind)
        data = dict(init_data)
        time_now = int(json[0][1]['time'])
        background_data = json[0][1]['backgroundData']
        template_data = json[2][1]
        slider_data = template_data['js_ResourceSlider']['slider']
        end_upgrade_time = int(background_data[view + 'EndUpgradeTime'])  # resourceEndUpgradeTime / tradegoodEndUpgradeTime
        upgrading = end_upgrade_time > 0
        if upgrading:
            end_upgrade_time = daysHoursMinutes(int(end_upgrade_time) - time_now)
        data.update({
            # workplace related
            'material': material_ind,
            'level': background_data[view + 'Level'],  # resourceLevel / tradegoodLevel
            'upgrading': upgrading,
            'upgradeEndTime': end_upgrade_time,
            'production': float(str(template_data['js_resource_tooltip_total_production']['text']).replace(',', '')),
            'totalWorkers': _get_int(template_data['valueWorkers']),
            'maxWorkers': _get_int(slider_data['max_value']),
            'overchargedWorkers': _get_int(slider_data['overcharge']),
            # city related
            'availableWood': _get_int(json[0][1]['headerData']['currentResources']['resource']),
            'freeCitizens': _get_int(template_data['valueCitizens']),
            'goldPerHour': float(str(template_data['valueWorkCosts']).replace(',', '')),
        })

        if not data['upgrading'] and json[1][0] == 'changeView':
            # changeView -> resources
            matches = re.findall(r'<li class="wood">(.*?)</li>', json[1][1][1])
            if len(matches) == 2:
                needed, donated = matches
                free_deposit = "0"
            else:
                needed, donated, free_deposit = matches

            data['requiredWoodForNextLevel'] = get_number(needed) - get_number(donated)
            data['freeDonationWood'] = get_number(free_deposit)
        else:
            data['requiredWoodForNextLevel'] = init_data.get("requiredWoodForNextLevel", 0)
            data['freeDonationWood'] = init_data.get("freeDonationWood", 0)

        return data

    def open_city_window(city_id):
        return ikariam_service.get(config.city_url + city_id)

    def open_island_window(island_id):
        return ikariam_service.get(config.island_url + island_id)

    def open_workplace_window(material_ind, island_id):
        return ikariam_service.post(params={
            'view': get_view(material_ind),
            'type': 'resource' if material_ind == 0 else material_ind,
            'islandId': island_id,
            'backgroundView': 'island',
            'currentIslandId': island_id,
            'actionRequest': config.actionRequest,
            'ajax': '1'
        })

    def get_workplace_data(init_data, material_ind, island_id):
        """
        Retrieves data for workplace / resource information
        :param init_data: dict with city data
        :param material_ind: for which material to get data
        :param island_id: for which island to get data
        :return: resource dict
        """
        return extract_workplace_data(
            init_data,
            material_ind,
            json.loads(
                open_workplace_window(material_ind, island_id),
                strict=False
            )
        )

    def get_workplaces():
        """
        Retrieves workspaces data for current user
        :return: list[json workplaces]
        """
        [city_ids, cities] = getIdsOfCities(ikariam_service, False)
        loading_msg = "Loading workplaces for cities"
        all_workplaces = 3 * len(city_ids)

        workplaces = []

        for city_ind, city_id in enumerate(city_ids):
            printProgressBar(loading_msg, city_ind*3+1, all_workplaces)
            city = getCity(open_city_window(city_id))

            island_id = city['islandId']
            city_data = {
                'cityId': city['id'],
                'cityName': city['cityName'],
                'islandId': island_id,
            }
            open_island_window(island_id)

            printProgressBar(loading_msg, city_ind*3+2, all_workplaces)
            workplaces.append(get_workplace_data(city_data, 0, island_id))

            printProgressBar(loading_msg, city_ind*3+3, all_workplaces)
            workplaces.append(get_workplace_data(city_data, cities[city_id]['tradegood'], island_id))

        return workplaces

    def print_workplaces(workplaces):
        """
        Prints workplaces to the user
        :param workplaces: json workplaces list
        :return: None
        """
        banner()

        # Print table header
        print(column_separator.join([rightAlign(c, cl) for c, cl in zip(columns, column_length)]))

        # Print table
        for ind, workplace in enumerate(workplaces):
            print_city_name = ind % 2 == 0
            if print_city_name:
                # print separator between cities
                print('-' * (sum(column_length) + (len(column_length) - 1) * len(column_separator)))

            total_workers = workplace['totalWorkers']
            max_workers = workplace['maxWorkers']
            material = workplace['material']
            upgrading = workplace['upgrading']
            overcharged = workplace['overchargedWorkers']
            free_citizens = workplace['freeCitizens']
            gold_per_hour = workplace['goldPerHour']
            free_donation = workplace['freeDonationWood']

            city_stats_colour = ''
            if print_city_name:
                if free_citizens > 0:
                    city_stats_colour = Colours.Text.Light.GREEN
            else:
                if gold_per_hour < 0:
                    city_stats_colour = Colours.Text.Light.RED
                else:
                    city_stats_colour = Colours.Text.Light.YELLOW

            # Construct colours for data
            colours = [
                '',
                '' if print_city_name else Colours.MATERIALS[0],
                city_stats_colour,
                Colours.MATERIALS[material],
                '',
                Colours.Text.Light.GREEN if total_workers >= max_workers else Colours.Text.Light.RED,
                Colours.Text.Light.YELLOW if total_workers > max_workers else '',
                Colours.Text.Light.GREEN if upgrading else '',
                Colours.Text.Light.YELLOW if upgrading else '',
                '',
            ]

            city_column = workplace['cityName']
            if not print_city_name:
                city_column = "{} free Wood".format(
                    addThousandSeparator(workplace['availableWood'])
                )

            if print_city_name:
                city_stats_column = "{} Idle People".format(free_citizens)
            else:
                city_stats_column = "{} gold/h".format(
                    addThousandSeparator(gold_per_hour, include_sign=True)
                )

            # Construct data
            row = [
                str(ind+1) + ")",
                city_column,
                city_stats_column,
                materials_names[material],
                '+{}/h'.format(addThousandSeparator(workplace['production'])),
                "{} / {}".format(
                    addThousandSeparator(min(total_workers, max_workers)),
                    addThousandSeparator(max_workers)
                ),
                "{} / {}".format(
                    0 if overcharged == 0 else max(0, total_workers - max_workers),
                    overcharged
                ),
                workplace['level'] + ('+' if upgrading else ' '),
                addThousandSeparator(workplace['requiredWoodForNextLevel']) if not upgrading else "Upgrading for " + workplace['upgradeEndTime'],
                addThousandSeparator(free_donation)
            ]

            # Combine and print
            print(column_separator.join([
                (colour + rightAlign(data, length) + Colours.Text.RESET)
                for colour, data, length in zip(colours, row, column_length)
            ]))

    def wait_for_action(workplaces_length):
        """
        Prints actions and waits the user to select action
        :param workplaces_length:
        :return: [action, workplaceId]
        """
        print("\n\nActions:\n")
        for i, a in enumerate(actions):
            print(" {: >2}) {}".format(i, a))
        print()
        action_id = read(min=0, max=len(actions)-1, digit=True)
        if actions[action_id] == action_exit:
            return [action_id, action_id]

        msg = "\nSelect target workplace between 1 and {}: ".format(workplaces_length)
        workplace_id = read(msg=msg, min=1, max=workplaces_length, digit=True)

        return [action_id, workplace_id]

    def donate(workplace):
        """
        Perform the donation
        :param workplace: where to donate
        :return: json workplace (after the update)
        """
        input_max = "max"

        if workplace['upgrading']:
            print('Already in process of upgrading. Have to wait', workplace['upgradeEndTime'])
            return workplace

        _available_wood = workplace['availableWood'] + workplace['freeDonationWood']
        print(
            "Free wood in town: ",
            addThousandSeparator(_available_wood)
        )
        maximum_donation = min(
            _available_wood,
            workplace['requiredWoodForNextLevel']
        )

        print()
        print('Enter donation amount between 1 and {}.'.format(
            addThousandSeparator(maximum_donation))
        )
        print('Or type "{}" for maximum: '.format(input_max))
        donation = read(min=1, max=maximum_donation, digit=True,
                        additionalValues=[input_max])

        if donation == input_max:
            donation = maximum_donation

        execute = read(
            msg="{} wood will be donated. Continue? [Y/N]".format(addThousandSeparator(donation)),
            values=['y', 'Y', 'n', 'N']
        )

        if execute.lower() == 'n':
            print("Aborting...")
            return workplace

        print("\nDonating {} wood to {} workplace from {}".format(
            addThousandSeparator(donation),
            materials_names[workplace['material']],
            workplace['cityName']
        ))
        
        return extract_workplace_data(
            workplace,
            workplace['material'],
            json.loads(
                ikariam_service.post(params={
                    'type': get_view(workplace['material']),
                    'islandId': workplace['islandId'],
                    'currentIslandId': workplace['islandId'],
                    'action': 'IslandScreen',
                    'function': 'donate',
                    'donation': donation,
                    'backgroundView': 'island',
                    'templateView': get_view(workplace['material']),
                    'actionRequest': actionRequest,
                    'ajax': '1'
                }),
                strict=False
            )
        )

    def set_workers(workplace):
        """
        Set the new workers
        :param workplace: where to set the new workers
        :return: json workplace (after the update)
        """
        input_max_workers = 'max'
        input_max_hands = 'full'

        current_workers = workplace['totalWorkers']
        free_citizens = workplace['freeCitizens']
        max_workers = min(
            current_workers + free_citizens,
            workplace['maxWorkers'] + workplace['overchargedWorkers']
        )

        print('Free citizens  :', free_citizens)
        print('Current workers:', current_workers)
        print('Maximum workers:', max_workers)

        print()
        print('Enter new workers between 0 and {} '.format(max_workers))
        print('({} workers + {} helping hands)'.format(
            workplace['maxWorkers'], workplace['overchargedWorkers']))
        print('Or type "{}" for maximum workers'.format(input_max_workers))
        print('Or "{}" for maximum with helping hands'.format(input_max_hands))
        workers = read(min=0, max=max_workers, digit=True,
                       additionalValues=[input_max_workers, input_max_hands])

        if workers == input_max_workers:
            workers = min(max_workers, workplace['maxWorkers'])
        elif workers == input_max_hands:
            workers = max_workers

        print("\nSetting {} to work!".format(workers))

        return extract_workplace_data(
            workplace,
            workplace['material'],
            json.loads(
                ikariam_service.post(params={
                    'action': 'IslandScreen',
                    'function': 'workerPlan',
                    'type': get_view(workplace['material']),
                    'islandId': workplace['islandId'],
                    'cityId': workplace['cityId'],
                    'screen': get_view(workplace['material']),
                    get_view(workplace['material'])[0] + 'w': workers, # rw/tw
                    'backgroundView': 'island',
                    'currentIslandId': workplace['islandId'],
                    'templateView': get_view(workplace['material']),
                    'actionRequest': actionRequest,
                    'ajax': '1'
                }),
                strict=False
            )
        )
    # endregion

    workplaces = get_workplaces()

    while True:
        print_workplaces(workplaces)

        [action_id, workplace_id] = wait_for_action(len(workplaces))
        action = actions[action_id]

        if action == action_exit:
            break

        workplace_ind = workplace_id - 1
        workplace = workplaces[workplace_ind]

        # Simulate person
        open_city_window(workplace['cityId'])  # change city
        open_island_window(workplace['islandId'])
        workplace = get_workplace_data(
            workplace,
            workplace['material'],
            workplace['islandId']
        )

        print("\n")
        print("     City: ", workplace['cityName'])
        print("Workplace: ", materials_names[workplace['material']])

        if action == action_donate:
            workplace = donate(workplace)
        elif action == action_change_workers:
            workplace = set_workers(workplace)
        else:
            print("Unknown action ", action)

        # update all other workplaces related to this city
        for ind, wp in enumerate(workplaces):
            if wp['cityId'] == workplace['cityId'] and ind != workplace_ind:
                wp['availableWood'] = workplace['availableWood']
                wp['freeCitizens'] = workplace['freeCitizens']
                wp['goldPerHour'] = workplace['goldPerHour']
            elif wp['islandId'] == workplace['islandId'] and wp['material'] == workplace['material']:
                wp['availableWood'] = workplace['availableWood']
                wp['upgradeEndTime'] = workplace['upgradeEndTime']
                wp['upgrading'] = workplace['upgrading']

        # update operational workplace
        workplaces[workplace_ind] = workplace

        print("\nOperation is successful!")
        enter()
