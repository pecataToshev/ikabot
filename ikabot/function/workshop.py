#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import time
from typing import List, Tuple

from bs4 import BeautifulSoup

from ikabot.config import actionRequest
from ikabot.helpers.buildings import choose_city_with_building
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import parse_int
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, daysHoursMinutes, decodeUnicodeEscape, enter, \
    printTable
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


def extract_url_parameters(url: str) -> dict:
    return dict(re.findall(r'(\w+)=(\w+)', url))


def extract_units_data(html: str) -> Tuple[bool, List[dict]]:
    soup = BeautifulSoup(html, 'html.parser')
    _groups = soup.find_all(lambda tag: tag.name == 'div' and tag.get('id') in ['tabUnits', 'tabShips'])

    _units = []
    _has_upgrade = False

    for _group in _groups:
        _units_tab_params = extract_url_parameters(soup.find(id='js_'+_group.get('id'))['onclick'])
        _units_type = _group.find('h3', {'class': 'header'}).text.strip()
        _units_html = _group.find_all('div', {'class': 'units'})
        for _u in _units_html:
            _unit_name = _u.find('div', {'class': 'object'})['title']
            _added_unit_definition = False
            for _t in _u.find_all('table'):
                _res = _t.find('td', {'class': 'res'})

                _upgrade_html = _t.find('td', {'class': 'upgrade_desc'})
                _action_buttons = _upgrade_html.find_all('div', {'class': 'actionButton'})
                if len(_action_buttons) > 0:
                    _action = _action_buttons[0].find('a')['title']
                elif _upgrade_html.find('div', {'id': 'upgradeProgress'}):
                    _timing_str = re.search(r'getProgressBar\((.*?)\);', html, re.DOTALL).group(1)
                    _enddate_match = re.search(r'enddate: (\d+)', _timing_str).group(1)
                    _currentdate_match = re.search(r'currentdate: (\d+)', _timing_str).group(1)

                    _action = 'Upgrading in progress for {}'.format(daysHoursMinutes(int(_enddate_match)
                                                                                     - int(_currentdate_match)))

                    _has_upgrade = True
                else:
                    _action = _upgrade_html.find_all('span')[0].text

                _can_upgrade = len(_action_buttons) == 1
                _unit = {
                    'tab': _group.get('id'),
                    'tableName': _unit_name if _added_unit_definition else _units_type,
                    'type': _units_type,
                    'name': _unit_name,
                    'improvement': _t.find('img')['title'].strip(),
                    'glass': parse_int(_res.find('li', {'class': 'glass'}).text),
                    'gold': parse_int(_res.find('li', {'class': 'gold'}).text),
                    'time': _res.find('li', {'class': 'time'}).text.strip(),
                    'upgrade': re.sub(r'\s+', ' ', _upgrade_html.find('p').text.strip()),
                    'action': _action,
                    'canUpgrade': _can_upgrade,
                    'insufficientResources': len(_action_buttons) == 2,
                    'upgradeParams': extract_url_parameters(_action_buttons[0].find('a')['href']) if _can_upgrade else None,
                    'unitTabParams': _units_tab_params,
                }
                _added_unit_definition = True

                _units.append(_unit)

    return _has_upgrade, _units


def use_workshop(ikariam_service: IkariamService, db: Database, telegram: Telegram):

    banner()
    _selected_building_data = choose_city_with_building(ikariam_service, 'workshop')
    if _selected_building_data is None:
        return

    (city, building, data) = _selected_building_data

    banner()
    print(city['name'])

    change_view_data = data[1][1][1]
    has_upgrade, units = extract_units_data(change_view_data)

    def __determine_action_color(action: str, row: dict):
        if row['insufficientResources'] or has_upgrade:
            return Colours.Text.YELLOW
        if row['canUpgrade']:
            return Colours.Text.GREEN
        else:
            return Colours.Text.RED

    printTable(
        table_config=[
            {'title': 'ID', 'useDataRowIndexForValue': lambda data_index: data_index + 1,
             'setColour': __determine_action_color},
            {'key': 'tableName', 'title': 'Name', 'fmt': decodeUnicodeEscape, 'align': '<'},
            {'key': 'glass', 'title': 'Glass', 'setColour': lambda v, r: Colours.MATERIALS[3],
             'fmt': addThousandSeparator},
            {'key': 'gold', 'title': 'Gold', 'fmt': addThousandSeparator},
            {'key': 'time', 'title': 'Upgrade Time', 'align': '^'},
            {'key': 'upgrade', 'title': 'Upgrade', 'fmt': decodeUnicodeEscape},
            {'key': 'action', 'title': 'Action', 'fmt': decodeUnicodeEscape, 'setColour': __determine_action_color},
        ],
        table_data=units,
        row_additional_indentation='  ',
        missing_value='',
        print_row_separator=lambda row_index: row_index % 2 == 0
    )

    print('\n 0) Exit')
    _selected_improvement = read(msg='Enter the ID of the improvement you wish to use: ', digit=True,
                                 min=0, max=len(units))

    if _selected_improvement == 0:
        return

    _selected_improvement -= 1  # move to index
    _selected_unit = units[_selected_improvement]

    if has_upgrade:
        print("There's an upgrade at the moment")
        enter()
        return
    elif _selected_unit['insufficientResources']:
        print("Insufficient resources")
        enter()
        return
    elif not _selected_unit['canUpgrade']:
        print("Can't upgrade: {}".format(_selected_unit['action']))
        enter()
        return

    # region Select the correct tab
    _params = _selected_unit['unitTabParams']
    _params.update({
        'backgroundView': 'city',
        'currentCityId': city['id'],
        'actionRequest': actionRequest,
        'ajax': '1'
    })

    ikariam_service.post(
        noIndex=True,
        params=_params
    )

    # endregion

    time.sleep(1)

    # region Start improvement
    _params = _selected_unit['upgradeParams']
    _params.update({
        'activeTab': _selected_unit['tab'],
        'templateView': 'workshop',
        'backgroundView': 'city',
        'currentCityId': city['id'],
        'actionRequest': actionRequest,
        'ajax': '1'
    })

    ikariam_service.post(
        noIndex=True,
        params=_params
    )
    # endregion

    print("Started upgrading {}.".format(_selected_unit['name']))
    enter()
