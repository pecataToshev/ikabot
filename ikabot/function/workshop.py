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
from ikabot.helpers.gui import (Colours, addThousandSeparator, banner,
                                daysHoursMinutes, decodeUnicodeEscape, enter,
                                printTable)
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
            # Try to find unit name in different possible locations
            _unit_name_element = _u.find('div', {'class': 'object'})
            if _unit_name_element is None:
                # Try alternative location: div.unitDisplay
                _unit_name_element = _u.find('div', {'class': 'unitDisplay'})
            
            if _unit_name_element is None or 'title' not in _unit_name_element.attrs:
                # Skip this unit if we can't find the name element
                continue
            
            _unit_name = _unit_name_element['title']
            _added_unit_definition = False
            
            # Try old table-based structure first
            tables = _u.find_all('table')
            if len(tables) > 0:
                # Old HTML structure with tables
                for _t in tables:
                    _res = _t.find('td', {'class': 'res'})
                    if _res is None:
                        continue

                    _upgrade_html = _t.find('td', {'class': 'upgrade_desc'})
                    if _upgrade_html is None:
                        continue
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
                    
                    # Extract improvement title safely
                    _img = _t.find('img')
                    _improvement = _img['title'].strip() if _img and 'title' in _img.attrs else 'Unknown'
                    
                    # Extract resources safely
                    _glass_elem = _res.find('li', {'class': 'glass'})
                    _gold_elem = _res.find('li', {'class': 'gold'})
                    _time_elem = _res.find('li', {'class': 'time'})
                    
                    if not all([_glass_elem, _gold_elem, _time_elem]):
                        continue
                    
                    # Extract upgrade description safely
                    _upgrade_p = _upgrade_html.find('p')
                    _upgrade_desc = re.sub(r'\s+', ' ', _upgrade_p.text.strip()) if _upgrade_p else ''
                    
                    _unit = {
                        'tab': _group.get('id'),
                        'tableName': _unit_name if _added_unit_definition else _units_type,
                        'type': _units_type,
                        'name': _unit_name,
                        'improvement': _improvement,
                        'glass': parse_int(_glass_elem.text),
                        'gold': parse_int(_gold_elem.text),
                        'time': _time_elem.text.strip(),
                        'upgrade': _upgrade_desc,
                        'action': _action,
                        'canUpgrade': _can_upgrade,
                        'insufficientResources': len(_action_buttons) == 2,
                        'upgradeParams': extract_url_parameters(_action_buttons[0].find('a')['href']) if _can_upgrade else None,
                        'unitTabParams': _units_tab_params,
                    }
                    _added_unit_definition = True

                    _units.append(_unit)
            else:
                # New HTML structure with div.highlightbox
                highlightboxes = _u.find_all('div', {'class': 'highlightbox'})
                for _hb in highlightboxes:
                    # Extract improvement image and title
                    _img = _hb.find('img', {'class': 'newImage'})
                    if _img is None or 'alt' not in _img.attrs:
                        continue
                    _improvement = _img['alt'].strip()
                    
                    # Find upgrade description and action buttons
                    _upgrade_html = _hb.find('div', {'class': 'upgrade_desc'})
                    if _upgrade_html is None:
                        continue
                    
                    _action_buttons = _hb.find_all('div', {'class': 'actionButton'})
                    if len(_action_buttons) > 0:
                        _action_link = _action_buttons[0].find('a')
                        if _action_link:
                            _action = _action_link.get('title', 'Upgrade available')
                        else:
                            _action = 'Cannot upgrade'
                    elif _hb.find('div', {'id': 'upgradeProgress'}):
                        _timing_str = re.search(r'getProgressBar\((.*?)\);', html, re.DOTALL)
                        if _timing_str:
                            _enddate_match = re.search(r'enddate: (\d+)', _timing_str.group(1))
                            _currentdate_match = re.search(r'currentdate: (\d+)', _timing_str.group(1))
                            if _enddate_match and _currentdate_match:
                                _action = 'Upgrading in progress for {}'.format(
                                    daysHoursMinutes(int(_enddate_match.group(1)) - int(_currentdate_match.group(1)))
                                )
                                _has_upgrade = True
                            else:
                                _action = 'Upgrading in progress'
                        else:
                            _action = 'Upgrading in progress'
                    else:
                        _spans = _upgrade_html.find_all('span')
                        _action = _spans[0].text if len(_spans) > 0 else 'Unknown status'
                    
                    _can_upgrade = len(_action_buttons) > 0 and _action_buttons[0].find('a') is not None
                    
                    # Extract resources from ul.resources
                    _resources_ul = _hb.find('ul', {'class': 'resources'})
                    if _resources_ul is None:
                        continue
                    
                    _glass_elem = _resources_ul.find('li', {'class': 'glass'})
                    _gold_elem = _resources_ul.find('li', {'class': 'gold'})
                    _time_elem = _resources_ul.find('li', {'class': 'time'})
                    
                    if not all([_gold_elem, _time_elem]):
                        continue
                    
                    # Glass might not be present for all upgrades
                    _glass_value = parse_int(_glass_elem.text) if _glass_elem else 0
                    
                    # Extract upgrade description
                    _upgrade_p = _upgrade_html.find('p')
                    _upgrade_desc = re.sub(r'\s+', ' ', _upgrade_p.text.strip()) if _upgrade_p else ''
                    
                    # Get full upgrade text
                    _upgrade_full_text = re.sub(r'\s+', ' ', _upgrade_html.get_text(strip=True))
                    
                    _unit = {
                        'tab': _group.get('id'),
                        'tableName': _unit_name if _added_unit_definition else _units_type,
                        'type': _units_type,
                        'name': _unit_name,
                        'improvement': _improvement,
                        'glass': _glass_value,
                        'gold': parse_int(_gold_elem.text),
                        'time': _time_elem.text.strip(),
                        'upgrade': _upgrade_full_text,
                        'action': _action,
                        'canUpgrade': _can_upgrade,
                        'insufficientResources': len(_action_buttons) > 1,
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
