#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.config import actionRequest
from ikabot.helpers.buildings import choose_city_with_building
from ikabot.helpers.database import Database
from ikabot.helpers.gui import banner, enter, printTable
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.web.ikariamService import IkariamService


def calculate_conversion(population: int, number_of_priests: int, slider: dict) -> float:
    # It's not the right formula, but it does some job
    _start_conversion = float(number_of_priests * slider['callback_data']['citizens_per_priest'])
    constraint = float(slider['bottom_constraint']) / slider['top_constraint']
    return max(((_start_conversion - constraint) / population) * 100, 0)


def use_temple(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()
    _selected_building_data = choose_city_with_building(ikariam_service, 'temple')
    if _selected_building_data is None:
        return

    (city, temple, data) = _selected_building_data

    banner()
    print(city['name'])

    update_global_data = data[0][1]
    population = update_global_data['headerData']['currentResources']['population']

    template_data = data[2][1]
    slider = template_data['js_TempleSlider']['slider']

    # Print current data
    current_priests = slider['ini_value']
    print('Current priests:', current_priests)
    print('Current conversion rate: {:.2f}%'.format(calculate_conversion(population, current_priests, slider)))

    # Prepare common conversion percentages
    _table = []
    for _priests in range(slider['max_value']):
        _c = calculate_conversion(population, _priests, slider)
        _threshold = 0.1  # adjust the threshold as needed

        _closest_divisible = round(_c / 25) * 25
        if abs(_c - _closest_divisible) < _threshold:
            _table.append({'priests': _priests, 'conversionRate': _c})

    print('Common conversion percentages')
    printTable(
        table_config=[
            {'key': 'priests', 'title': '# Priests'},
            {'key': 'conversionRate', 'title': 'Conversion Rate', 'fmt': lambda v: '{:.2f}%'.format(v)},
        ],
        table_data=_table,
    )

    # Choose number of priests
    while True:
        new_priests_number = read(min=0, max=slider['max_value'],
                                     msg='Choose number of priests (max {}): '.format(slider['max_value']), digit=True)

        print('You chose {} priest(s)'.format(new_priests_number))
        print('The new conversion rate is {:.2f}%'.format(calculate_conversion(population, new_priests_number, slider)))
        if askUserYesNo('Proceed with setting'):
            break

        print("Ok. Let's try again")

    # Set number of priests
    ikariam_service.post(
        noIndex=True,
        params={
            'action': 'CityScreen',
            'function': 'assignPriests',
            'templateView': 'temple',
            'priests': new_priests_number,
            'cityId': city['id'],
            'position': temple['position'],
            'backgroundView': 'city',
            'currentCityId': city['id'],
            'actionRequest': actionRequest,
            'ajax': '1'
        },
    )

    print('Priests set in ' + city['name'])
    enter()
