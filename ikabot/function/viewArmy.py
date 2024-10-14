#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import Callable, Dict, List, Tuple

from bs4 import BeautifulSoup
from numpy import number

from ikabot.config import city_url, materials_names, MAXIMUM_CITY_NAME_LENGTH, actionRequest
from ikabot.function.constructBuilding import constructBuilding
from ikabot.function.islandWorkplaces import islandWorkplaces
from ikabot.function.transportGoodsBotConfigurator import transport_goods_bot_configurator
from ikabot.function.upgradeBuildingBotConfigurator import upgrade_single_building_bot_configurator
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, decodeUnicodeEscape, enter, printProgressBar
from ikabot.helpers.market import printGoldForAllCities
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


class CityArmyData:
    def __init__(self, city: dict[str, str], units: dict[str, number], units_order: List[str], fleet: dict[str, number], fleet_order: List[str]):
        self.city = city
        self.units = units
        self.units_order = units_order
        self.fleet = fleet
        self.fleet_order = fleet_order


def viewArmy(ikariam_service: IkariamService, db: Database, telegram: Telegram):

    # region Config
    COLUMN_SEPARATOR = ' | '
    STORAGE_COLUMN_MAX_LENGTH = 10
    RESOURCE_COLUMN_MAX_LENGTH = 10
    TABLE_WIDTH = MAXIMUM_CITY_NAME_LENGTH + RESOURCE_COLUMN_MAX_LENGTH + len(materials_names) * RESOURCE_COLUMN_MAX_LENGTH + (len(materials_names) + 2 - 1) * len(COLUMN_SEPARATOR)
    TABLE_ROW_SEPARATOR = '-' * TABLE_WIDTH
    TOTAL = 'TOTAL'

    def get_increment(incr):
        if incr == 0:
            return " " * RESOURCE_COLUMN_MAX_LENGTH
        colour = Colours.Text.Light.GREEN if incr > 0 else Colours.Text.Light.RED
        res_incr = "{: >{len}}".format(str(format(incr, '+,')), len=RESOURCE_COLUMN_MAX_LENGTH)
        return colour + res_incr + Colours.Text.RESET

    def get_storage(capacity, available):
        res = "{: >{len}}".format(str(format(available, ',')), len=RESOURCE_COLUMN_MAX_LENGTH)
        if capacity * 0.2 > capacity - available:
            res = Colours.Background.Light.RED + res + Colours.Background.RESET
        return res


    def _extract_units(html: str, root_id: str) -> (dict[str, number], List[str]):
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

    def _get_city_army_data(_city_id: number) -> CityArmyData:
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

    def print_vertical(prefix_length, words, separator=COLUMN_SEPARATOR):
        max_length = max(len(word) for word in words)
        # Pad each word with spaces to make them equal in length
        padded_words = [word.rjust(max_length) for word in words]

        # Create a matrix with characters aligned
        matrix = [list(row) for row in zip(*padded_words)]

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

        print_vertical(_max_city_name_length, _army_order)
        for _city_name, _army in zip(_city_names, _cities_army):
            _row = ["{: >{}}{}".format(_city_name, _max_city_name_length, COLUMN_SEPARATOR)]
            for _unit, _max_length in zip(_army_order, _max_length_per_army):
                _row.append("{: >{}}{}".format(addThousandSeparator(_army[_unit]), _max_length, COLUMN_SEPARATOR))
            print("".join(_row))



    def _print_all_army_table(_cities_army_data: List[CityArmyData]):
        _print_units(_cities_army_data, lambda c: (c.units, c.units_order))
        # print("\n\n\n\nBuildings:\n")
        # buildings_column_width = 5
        # constructed_building_names = get_building_names(_cities_army_data)
        # max_building_name_length = max(len(b) for b in constructed_building_names)
        # city_names = [c['name'] for c in _cities_army_data]
        # print_vertical(max_building_name_length - 1, city_names, ' ' * buildings_column_width)
        # print("-" * (max_building_name_length + (buildings_column_width + 1) * len(_cities_army_data)))
        # # gow many times we've encountered a building in the city. This is being
        # # done to display the duplicates
        # # {townHall: {city1: 1}, storage: {city1: 2}}
        # buildings_in_city_count = {}
        # for building_name in constructed_building_names:
        #     row = ["{: >{len}}".format(building_name, len=max_building_name_length)]
        #     encounters = buildings_in_city_count.get(building_name, {})
        #     for city in _cities_army_data:
        #         required_number = encounters.get(city['cityName'], 0)
        #         current_number = 0
        #
        #         building = None
        #         for pos in city['position']:
        #             if building_name == pos['name']:
        #                 if current_number == required_number:
        #                     building = pos
        #                     break
        #                 else:
        #                     current_number += 1
        #
        #         encounters.update({city['cityName']: current_number + 1})
        #         if building is None:
        #             row.append(" - ")
        #             continue
        #
        #         if building['isMaxLevel'] is True:
        #             colour = Colours.Text.Light.BLACK
        #         elif building['canUpgrade'] is True:
        #             colour = Colours.Text.Light.GREEN
        #         else:
        #             colour = Colours.Text.Light.RED
        #
        #         additional = '+' if building['isBusy'] is True else ' '
        #         row.append("{}{: >2}{}{}".format(colour, building['level'], additional, Colours.Text.RESET))
        #
        #     buildings_in_city_count.update({building_name: encounters})
        #     print(COLUMN_SEPARATOR.join(row))
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
