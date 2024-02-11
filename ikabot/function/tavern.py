#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from bs4 import BeautifulSoup

from ikabot.config import actionRequest, city_url
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import banner, Colours, decodeUnicodeEscape, enter, printTable
from ikabot.helpers.citiesAndIslands import chooseCity
from ikabot.helpers.satisfaction import get_satisfaction_level
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


def tavern(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    def __get_tavern(_city):
        for _building in _city['position']:
            if _building['building'] == 'tavern':
                return _building
        return None

    banner()

    print('City where manipulate wine consumption:')
    city = chooseCity(ikariam_service)
    city = getCity(ikariam_service.get(city_url + city['id']))

    tavern = __get_tavern(city)
    if tavern is None:
        print('There is no tavern in ' + city['name'])
        enter()
        return

    banner()
    print(city['name'])

    data = ikariam_service.post(
        noIndex=True,
        params={
            'view': 'tavern',
            'cityId': city['id'],
            'position': tavern['position'],
            'backgroundView': 'city',
            'currentCityId': city['id'],
            'actionRequest': actionRequest,
            'ajax': '1'
        }
    )
    data = json.loads(data, strict=False)

    change_view_data = data[1][1][1]
    options = BeautifulSoup(change_view_data, 'html.parser').find_all('option')

    template_data = data[2][1]
    template_params = json.loads(template_data['load_js']['params'], strict=False)

    start_satisfaction = template_params['startSatisfaction']

    table_data = [{'level': o['value'], 'name': o.text.strip(),
                   'wineSatisfaction': sat,
                   'saved': saved.replace('&nbsp;', ''),
                   'totalSatisfaction': start_satisfaction + sat,
                   'satisfactionClass': get_satisfaction_level(template_params['classNamePerSatisfaction'],
                                                               template_params['classValuePerSatisfaction'],
                                                               start_satisfaction + sat)
                   } for o, sat, saved in zip(options,
                                              template_params['satPerWine'],
                                              template_params['savedWine'])]

    printTable(
        table_config=[
            {'key': 'level', 'title': 'Level'},
            {'key': 'name', 'title': 'Wine Consumption', 'fmt': decodeUnicodeEscape},
            {'key': 'saved', 'title': 'Saved Wine'},
            {'key': 'wineSatisfaction', 'title': 'Wine Satisfaction'},
            {'key': 'totalSatisfaction', 'title': 'Total Satisfaction'},
            {'key': 'satisfactionClass', 'title': 'Satisfaction Class', 'setColor': lambda x: Colours.SATISFACTION[x]},
        ],
        table_data=table_data,
        row_color=lambda row_id, row_data: (
            Colours.Text.Light.YELLOW
            if row_data is not None and row_data['level'] == template_params['wineServeLevel']
            else ''
        ),
        row_additional_indentation='  ',
        missing_value='0'
    )

    wine_level = read(0, len(table_data) - 1, msg='Choose wine consumption level: ')

    ikariam_service.post(
        noIndex=True,
        params={
            'action': 'CityScreen',
            'function': 'assignWinePerTick',
            'templateView': 'tavern',
            'amount': wine_level,
            'cityId': city['id'],
            'position': tavern['position'],
            'backgroundView': 'city',
            'currentCityId': city['id'],
            'actionRequest': actionRequest,
            'ajax': '1'
        },
    )

    print('Wine consumption set')
    enter()
