#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
from typing import Callable, Dict, List, Tuple

from bs4 import BeautifulSoup

from ikabot.config import actionRequest, city_url
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, decodeUnicodeEscape, enter, formatTimestamp, \
    printProgressBar
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


class CityArmyData:
    def __init__(self, city: dict[str, str], units: dict[str, int], units_order: List[str], fleet: dict[str, int], fleet_order: List[str]):
        self.city = city
        self.units = units
        self.units_order = units_order
        self.fleet = fleet
        self.fleet_order = fleet_order


def viewArmy(ikariam_service: IkariamService, db: Database, telegram: Telegram):

    # region Config
    __column_separator = ' | '

    def _load_data(ikariam_service: IkariamService) -> List[CityArmyData]:
        banner()
        _data: List[CityArmyData] = []

        # region Retrieve cities _data
        [_city_ids, _] = getIdsOfCities(ikariam_service, False)
        for _res_ind, _city_id in enumerate(_city_ids):
            printProgressBar("Retrieving cities data", _res_ind+1, len(_city_ids))
            _data.append(_get_city_army_data(_city_id))

        return _data

    def _extract_units(html: str, root_id: str) -> (dict[str, int], List[str]):
        _soup = BeautifulSoup(html, 'html.parser')
        _tables = _soup.find('div', id=root_id).find_all('table', class_='militaryList')
        _data = {}
        _order = []
        for _table in _tables:
            _titles_row = _table.find('tr', class_='title_img_row').find_all('th')
            _counts_row = _table.find('tr', class_='count').find_all('td')
            _is_first = True
            for _title, _count in zip(_titles_row, _counts_row):
                if _is_first:
                    _is_first = False
                    continue
                _name = decodeUnicodeEscape(_title.text).strip()
                _order.append(_name)
                _data[_name] = _count.text.strip()
        return _data, _order

    def _get_city_army_data(_city_id: int) -> CityArmyData:
        _city = getCity(ikariam_service.get(city_url + _city_id))
        print(_city['name'])
        _json = ikariam_service.post(
            params={
                "view": "cityMilitary",
                "activeTab": "tabUnits",
                "cityId": _city_id,
                "backgroundView": "city",
                "currentCityId": _city_id,
                "actionRequest": actionRequest,
                "ajax": "1"
            }
        )
        _json = json.loads(_json, strict=False)
        _html = _json[1][1][1]
        _units, _units_order = _extract_units(_html, 'tabUnits')
        _fleet, _fleet_order = _extract_units(_html, 'tabShips')
        return CityArmyData(_city, _units, _units_order, _fleet, _fleet_order)


    def _print_vertical(prefix_length: int, words: List[str], columns_width: list[int], separator=__column_separator):
        max_length = max(len(word) for word in words)
        # Pad each word with spaces to make them equal in length
        padded_words = [word.rjust(max_length) for word in words]

        # Create a matrix with characters aligned
        matrix = [list(row) for row in zip(*padded_words)]

        # Center column over text
        for _r in range(len(matrix)):
            for _c in range(len(matrix[_r])):
                matrix[_r][_c] = "{:^{}}".format(matrix[_r][_c], columns_width[_c])

        # Print the matrix
        for row in matrix:
            print(separator.join([" " * prefix_length] + row))

    def _print_units(_cities_data: List[CityArmyData],
                     _extract_units: Callable[[CityArmyData], Tuple[Dict[str, int], List[str]]]):
        _minimum_unit_column_width = 4
        _city_names = [c.city['name'] for c in _cities_data]
        _max_city_name_length = max(len(c) for c in _city_names)

        (_, _army_order) = _extract_units(_cities_data[0])
        _cities_army = [units for units, _ in (_extract_units(c) for c in _cities_data)]
        _max_length_per_army = [max(len(addThousandSeparator(army[unit])) for army in _cities_army) for unit in _army_order]

        _short_army_order = [(s[:15] + '…') if len(s) > 16 else s for s in _army_order]
        _print_vertical(_max_city_name_length, _short_army_order, _max_length_per_army, separator=' '*len(__column_separator))
        print("-" * (_max_city_name_length + sum(_max_length_per_army) + len(_max_length_per_army) * len(__column_separator) + 1))
        for _city_name, _army in zip(_city_names, _cities_army):
            _row = ["{: >{}}".format(_city_name, _max_city_name_length)]
            for _unit, _max_length in zip(_army_order, _max_length_per_army):
                _num = int(_army[_unit])
                _num = ' ' if _num == 0 else addThousandSeparator(_num)
                _row.append("{}{: >{}}".format(__column_separator, _num, _max_length))
            print("".join(_row))
    # endregion

    _data: List[CityArmyData] = _load_data(ikariam_service)
    _data_time = time.time()
    # Remove progressbar
    banner()

    while True:
        print(" 0) Exit")
        print(" 1) Units")
        print(" 2) Fleet")
        print(" 3) Reload Data")
        _selected=read(min=0, max=3, digit=True)

        if _selected == 0:
            return

        if _selected == 3:
            _data = _load_data(ikariam_service)
            _data_time = time.time()
            continue

        banner()
        print("Data loaded on: {}\n".format(formatTimestamp(_data_time)))
        if _selected == 1:
            print("\tUNITS:\n")
            _print_units(_data, lambda c: (c.units, c.units_order))
        elif _selected == 2:
            print("\tFLEET:\n")
            _print_units(_data, lambda c: (c.fleet, c.fleet_order))

        print("\n\n")
    # THE END
