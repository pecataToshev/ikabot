#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging

from bs4 import BeautifulSoup

from ikabot.config import actionRequest, city_url, island_url, materials_names
from ikabot.helpers.citiesAndIslands import chooseCity
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity, getIsland
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, daysHoursMinutes, decodeUnicodeEscape, enter
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.web.ikariamService import IkariamService


def get_number(s):
    return int(s.replace(',', '').replace('.', ''))


def miracle_donate(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    print('Pick city to donate to miracle: ')
    city = chooseCity(ikariam_service)
    city = getCity(ikariam_service.get(city_url + city['id']))

    island = getIsland(ikariam_service.get(island_url + city['islandId']))

    miracle_json = ikariam_service.post(
        noIndex=True,
        params={
            'view': 'wonder',
            'islandId': island['id'],
            'backgroundView': 'island',
            'oldBackgroundView': 'island',
            'currentIslandId': island['id'],
            'actionRequest': actionRequest,
            'ajax': '1'
        }
    )
    miracle_json = json.loads(miracle_json, strict=False)

    change_view = BeautifulSoup(miracle_json[1][1][1], 'html.parser')
    resources = [int(p.get('name').replace('tradegood', '')) for p in
                 change_view.find('div', {'id': 'donate'}).find_all('input',
                                                                    attrs={'name': True, 'type': 'text'})]

    update_template_data = miracle_json[2][1]
    load_js_params = json.loads(update_template_data['load_js']['params'], strict=False)

    required_donations = get_number(update_template_data['js_donateNextLevel'])
    current_donations = get_number(update_template_data['js_donatedResources'])
    remaining_donations = required_donations - current_donations
    to_donate = [0] * len(materials_names)

    print()
    print('[{}:{}] {} ({})'.format(city['x'], city['y'], city['name'], island['name']))
    print('Wonder Data:')
    print('Name   : ', island['wonderName'])
    print("Level  : ", update_template_data['currentWonderLevel'])
    print("Belief : ", decodeUnicodeEscape(update_template_data['wonderBeliefInfo2']))
    print()

    if load_js_params['inProgress']:  # is upgrading
        seconds_left = int(load_js_params['endUpgradeTime']) - int(load_js_params['currentTime'])
        print('Currently upgrading. Will finish in {}'.format(daysHoursMinutes(seconds_left)))
        enter()
        return

    print("Remaining donations : ", addThousandSeparator(remaining_donations))

    print()
    print("Available resources :")
    for res in resources:
        print("{}{}: {}{}".format(Colours.MATERIALS[res], materials_names[res],
                                  addThousandSeparator(city['availableResources'][res]), Colours.Text.RESET))

    print()

    for res in resources:
        max_donation = min(remaining_donations, city['availableResources'][res])
        if max_donation == 0:
            continue
        print('How much {}{}{} would you like to donate (max: {})? '.format(
            Colours.MATERIALS[res], materials_names[res], Colours.Text.RESET,
            addThousandSeparator(max_donation)))
        t = read(min=0, max=max_donation, digit=True, default=0)
        to_donate[res] = t
        remaining_donations -= t

    if sum(to_donate) == 0:
        print('No donations made!')
        enter()
        return

    print()
    print('Will you donate:')
    for res in resources:
        print("{}{}: {}{}".format(Colours.MATERIALS[res], materials_names[res],
                                  addThousandSeparator(to_donate[res]), Colours.Text.RESET))

    print()
    if not askUserYesNo("Proceed"):
        return

    print("\nOk. Donating...")
    donate_params = {
        'islandId': island['id'],
        'action': 'IslandScreen',
        'function': 'wonderDonate',
        'backgroundView': 'island',
        'currentIslandId': island['id'],
        'templateView': 'wonder',
        'actionRequest': actionRequest,
        'ajax': '1',
    }

    for res in resources:
        donate_params['tradegood{}'.format(res)] = to_donate[res]

    response = ikariam_service.post(
        noIndex=True,
        params=donate_params
    )
    response = json.loads(response, strict=False)

    print(decodeUnicodeEscape(response[3][1][0]['text']))
    enter()
