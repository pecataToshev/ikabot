#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Callable, Dict, List, Tuple

from bs4 import BeautifulSoup

from ikabot.config import actionRequest, city_url
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, decodeUnicodeEscape, enter, printProgressBar
from ikabot.helpers.telegram import Telegram
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


    def get_building_names(cities):
        '''
        Returns a list of buildings names with unique and maximum number of
        buildings for all towns. e.g. [townHall, academy, storage, storage].
        Keep in mind that we allow duplicates in te response.
        :param cities: city
        :return: list of maximum number of unique buildings across all cities
        '''
        constructed_buildings = {}
        for city in cities:
            buildings = dict()
            for pos in city['position']:
                name = pos['name']
                if pos['position'] != 0 and name is not None and name != 'empty':
                    count = buildings.get(name, 0)
                    buildings.update({name: count + 1})
            constructed_buildings = {key: max(buildings.get(key, 0), constructed_buildings.get(key, 0)) for key in set(buildings) | set(constructed_buildings)}

        town_hall_name = [p['name'] for p in cities[0]['position'] if p['position'] == 0][0]

        return [town_hall_name] + sorted([key for key, value in constructed_buildings.items() for _ in range(value)])

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

        _print_vertical(_max_city_name_length, _army_order, _max_length_per_army, separator=' '*len(__column_separator))
        print("-" * (_max_city_name_length + sum(_max_length_per_army) + len(_max_length_per_army) * len(__column_separator) + 1))
        for _city_name, _army in zip(_city_names, _cities_army):
            _row = ["{: >{}}".format(_city_name, _max_city_name_length)]
            for _unit, _max_length in zip(_army_order, _max_length_per_army):
                _num = int(_army[_unit])
                _num = ' ' if _num == 0 else addThousandSeparator(_num)
                _row.append("{}{: >{}}".format(__column_separator, _num, _max_length))
            print("".join(_row))


    def _print_all_army_table(_cities_army_data: List[CityArmyData]):
        print("\n\n\tUNITS:\n\n")
        _print_units(_cities_army_data, lambda c: (c.units, c.units_order))
        print("\n\n\n")
        print("\n\n\tFLEET:\n\n")
        _print_units(_cities_army_data, lambda c: (c.fleet, c.fleet_order))
    # endregion

    banner()

    [city_ids, _] = getIdsOfCities(ikariam_service, False)
    data: List[CityArmyData] = []

    # region Retrieve cities data
    for res_ind, city_id in enumerate(city_ids):
        printProgressBar("Retrieving cities data", res_ind+1, len(city_ids))
        data.append(_get_city_army_data(city_id))
    # endregion

    # Remove progressbar
    banner()
    _print_all_army_table(data)

    enter()
    # THE END
