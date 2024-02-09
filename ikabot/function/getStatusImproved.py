#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.config import city_url, materials_names, MAXIMUM_CITY_NAME_LENGTH
from ikabot.function.constructBuilding import constructBuilding
from ikabot.function.islandWorkplaces import islandWorkplaces
from ikabot.function.transportGoodsBotConfigurator import transport_goods_bot_configurator
from ikabot.function.upgradeBuildingBotConfigurator import upgrade_building_bot_configurator
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import banner, Colours, printProgressBar
from ikabot.helpers.market import printGoldForAllCities
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


def getStatusForAllCities(ikariam_service: IkariamService, db: Database, telegram: Telegram):

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
        color = Colours.Text.Light.GREEN if incr > 0 else Colours.Text.Light.RED
        res_incr = "{: >{len}}".format(str(format(incr, '+,')), len=RESOURCE_COLUMN_MAX_LENGTH)
        return color + res_incr + Colours.Text.RESET

    def get_storage(capacity, available):
        res = "{: >{len}}".format(str(format(available, ',')), len=RESOURCE_COLUMN_MAX_LENGTH)
        if capacity * 0.2 > capacity - available:
            res = Colours.Background.Light.RED + res + Colours.Background.RESET
        return res

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

    def print_buildings(__cities):
        print("\n\n\n\nBuildings:\n")
        buildings_column_width = 5
        constructed_building_names = get_building_names(__cities)
        max_building_name_length = max(len(b) for b in constructed_building_names)
        city_names = [c['name'] for c in __cities]
        print_vertical(max_building_name_length - 1, city_names, ' ' * buildings_column_width)
        print("-" * (max_building_name_length + (buildings_column_width + 1) * len(__cities)))
        # gow many times we've encountered a building in the city. This is being
        # done to display the duplicates
        # {townHall: {city1: 1}, storage: {city1: 2}}
        buildings_in_city_count = {}
        for building_name in constructed_building_names:
            row = ["{: >{len}}".format(building_name, len=max_building_name_length)]
            encounters = buildings_in_city_count.get(building_name, {})
            for city in __cities:
                required_number = encounters.get(city['cityName'], 0)
                current_number = 0

                building = None
                for pos in city['position']:
                    if building_name == pos['name']:
                        if current_number == required_number:
                            building = pos
                            break
                        else:
                            current_number += 1

                encounters.update({city['cityName']: current_number + 1})
                if building is None:
                    row.append(" - ")
                    continue

                if building['isMaxLevel'] is True:
                    color = Colours.Text.Light.BLACK
                elif building['canUpgrade'] is True:
                    color = Colours.Text.Light.GREEN
                else:
                    color = Colours.Text.Light.RED

                additional = '+' if building['isBusy'] is True else ' '
                row.append("{}{: >2}{}{}".format(color, building['level'], additional, Colours.Text.RESET))

            buildings_in_city_count.update({building_name: encounters})
            print(COLUMN_SEPARATOR.join(row))

    def print_resource_table(__cities):
        # city |  storage | wood | wine | stone | crystal | sulfur
        print("\n\nResources:\n")
        materials = [(Colours.MATERIALS[ind] + "{: ^{len}}".format(r, len=RESOURCE_COLUMN_MAX_LENGTH) + Colours.Text.RESET)
                     for ind, r in enumerate(materials_names)]
        city_name_header_column = " " * MAXIMUM_CITY_NAME_LENGTH
        storage_header_column = "{: ^{len}}".format("Storage", len=STORAGE_COLUMN_MAX_LENGTH)
        print(COLUMN_SEPARATOR.join([city_name_header_column, storage_header_column] + materials))
        total = {
            'cityName': TOTAL,
            'storageCapacity': sum(c['storageCapacity'] for c in __cities),
            'availableResources': [sum(x) for x in zip(*[c['availableResources'] for c in __cities])],
            'productionPerHour': [sum(x) for x in zip(*[c['productionPerHour'] for c in __cities])],
            'wineConsumptionPerHour': sum(c['wineConsumptionPerHour'] for c in __cities)
        }
        for city in __cities + [total]:
            city_name = city['cityName']
            if city_name == TOTAL:
                print(TABLE_ROW_SEPARATOR.replace("-", "="))
            else:
                print(TABLE_ROW_SEPARATOR)

            storage_capacity = city['storageCapacity']
            available_resources = city['availableResources']
            row1 = [
                "{: >{len}}".format(city_name, len=MAXIMUM_CITY_NAME_LENGTH),
                "{: >{len}}".format(str(format(storage_capacity, ',')), len=STORAGE_COLUMN_MAX_LENGTH),
            ]
            row2 = [
                " " * MAXIMUM_CITY_NAME_LENGTH,
                " " * STORAGE_COLUMN_MAX_LENGTH,
                ]
            for res_ind, resource in enumerate(materials_names):
                res_in_storage = available_resources[res_ind]
                row1.append(Colours.MATERIALS[res_ind] + get_storage(storage_capacity, res_in_storage) + Colours.Text.RESET)

                res_incr = city['productionPerHour'][res_ind]
                if res_ind == 1:
                    res_incr -= city['wineConsumptionPerHour']
                row2.append(get_increment(res_incr))

            print(COLUMN_SEPARATOR.join(row1))
            print(COLUMN_SEPARATOR.join(row2))

    # endregion

    banner()

    [city_ids, _] = getIdsOfCities(ikariam_service, False)
    cities = []

    # available_ships = 0
    # total_ships = 0

    # region Retrieve cities data
    for res_ind, city_id in enumerate(city_ids):
        printProgressBar("Retrieving cities data", res_ind+1, len(city_ids))
        cities.append(getCity(ikariam_service.get(city_url + city_id)))
    # endregion

    # Remove progressbar
    banner()
    print_resource_table(cities)

    # region Actions
    while True:
        print("\n\n\nActions:")
        print("(0) Exit")
        print("(1) Print buildings")
        print("(2) Construction List")
        print("(3) Construct Building")
        print("(4) Send resources")
        print("(5) Workplaces")
        print("(6) Show gold")
        action = read(min=0, max=5, digit=True)
        if action == 0:
            break
        elif action == 1:
            print_buildings(cities)
        elif action == 2:
            return upgrade_building_bot_configurator(ikariam_service, db, telegram)
        elif action == 3:
            return constructBuilding(ikariam_service, db, telegram)
        elif action == 4:
            return transport_goods_bot_configurator(ikariam_service, db, telegram)
        elif action == 5:
            return islandWorkplaces(ikariam_service, db, telegram)
        elif action == 6:
            printGoldForAllCities(ikariam_service, city_ids[0])


    # endregion



