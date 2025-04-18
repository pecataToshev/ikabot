#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from ikabot.config import actionRequest, city_url
from ikabot.helpers.buildings import extract_target_building, \
    find_city_with_the_biggest_building, get_building_info
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, clear, enter
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo
from ikabot.web.ikariamService import IkariamService


def buy_ships(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    target_building_type = 'port'
    target_tab = 'tabBuyTransporter'

    port_city = find_city_with_the_biggest_building(ikariam_service, target_building_type)
    if port_city is None:
        print('No port found.')
        enter()
        return

    port = extract_target_building(port_city, target_building_type)
    # Only initial data. After that we get it with the buy
    port_info = get_building_info(ikariam_service, port_city['id'], port)

    # activate the right tab
    ikariam_service.post(
        noIndex=True,
        params={
            'view': target_building_type,
            'activeTab': target_tab,
            'cityId': port_city['id'],
            'position': port['position'],
            'backgroundView': 'city',
            'currentCityId': port_city['id'],
            'templateView': target_building_type,
            'actionRequest': actionRequest,
            'ajax': '1'
        }
    )

    while True:
        print("\n\n")

        available_gold = int(float(port_info[0][1]["headerData"]["gold"]))
        update_template_data = port_info[2][1]
        ship_cost = int(float((update_template_data['js_transporterCosts'].replace(',', '').replace('.', ''))))

        can_buy = "enabled" == update_template_data.get('js_buyTransporterAction', {}).get("buttonState", "")

        print('Available gold:           {}'.format(addThousandSeparator(available_gold)))
        print('Transporter cost:         {}'.format(addThousandSeparator(ship_cost)))
        print('Transporters available:   {}'.format(update_template_data['js_maxTransporter']))

        if not can_buy:
            print('You can\'t buy a transporter right now.')
            enter()
            return

        if not askUserYesNo('Do you want to buy a transporter for {}?'.format(addThousandSeparator(ship_cost))):
            return

        port_info = json.loads(ikariam_service.post(
            noIndex=True,
            params={
                'action': 'CityScreen',
                'function': 'increaseTransporter',
                'templateView': target_building_type,
                'activeTab': target_tab,
                'cityId': port_city['id'],
                'position': port['position'],
                'backgroundView': 'city',
                'currentCityId': port_city['id'],
                'actionRequest': actionRequest,
                'ajax': '1'
            },
        ), strict=False)
