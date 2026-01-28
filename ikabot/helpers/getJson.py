#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from math import ceil

from ikabot.config import SECONDS_IN_HOUR, materials_names
from ikabot.helpers.gui import decodeUnicodeEscape
from ikabot.helpers.resources import (extract_resource_production,
                                      extract_tradegood,
                                      extract_tradegood_production,
                                      getAvailableResources,
                                      getWarehouseCapacity,
                                      getWineConsumptionPerHour)


def parse_int(num) -> int:
    """Parse an integer from a string, handling abbreviated formats.
    
    Supports formats like:
    - "1,234" or "1.234" -> 1234
    - "1.5K" or "1,5K" -> 1500
    - "117M" or "1.17M" -> 117000000
    - "1kkk" -> 1000000000 (billions)
    - "1kk" -> 1000000 (millions)
    """
    num_str = str(num).strip().upper()
    
    # Handle abbreviated formats
    multiplier = 1
    if 'KKK' in num_str:
        multiplier = 1000000000
        num_str = num_str.replace('KKK', '')
    elif 'KK' in num_str:
        multiplier = 1000000
        num_str = num_str.replace('KK', '')
    elif 'M' in num_str:
        multiplier = 1000000
        num_str = num_str.replace('M', '')
    elif 'K' in num_str:
        multiplier = 1000
        num_str = num_str.replace('K', '')
    
    # Remove thousand separators (both comma and dot can be used as separators)
    # We need to be careful: "1.5K" means 1500, but "1.234.567" means 1234567
    # Generally, if there's only one dot/comma and it's followed by 1-2 digits, it's decimal
    # Otherwise, they're thousand separators
    
    # Count dots and commas
    dot_count = num_str.count('.')
    comma_count = num_str.count(',')
    
    if dot_count + comma_count == 0:
        # No separators, simple case
        return int(float(num_str) * multiplier)
    
    # If there's only one separator and it's followed by 1-2 digits at the end, treat as decimal
    # If followed by exactly 3 digits, treat as thousand separator
    if dot_count == 1 and comma_count == 0:
        parts = num_str.split('.')
        if len(parts) == 2 and len(parts[1]) <= 2 and parts[1].isdigit():
            # Decimal number like "1.5" or "1.23"
            return int(float(num_str) * multiplier)
        else:
            # Thousand separator like "1.234" or "1.234.567"
            num_str = num_str.replace('.', '')
    elif comma_count == 1 and dot_count == 0:
        parts = num_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2 and parts[1].isdigit():
            # Decimal number like "1,5" or "1,23"
            return int(float(num_str.replace(',', '.')) * multiplier)
        else:
            # Thousand separator like "1,234"
            num_str = num_str.replace(',', '')
    else:
        # Multiple separators - remove all as thousand separators
        num_str = num_str.replace('.', '').replace(',', '')
    
    return int(float(num_str) * multiplier)


def getFreeCitizens(html):
    """This function is used in the ``getCity`` function to determine the amount of free (idle) citizens in the given city.
    Parameters
    ----------
    html : str
        a string representing html which is returned when sending a get request to view a city.

    Returns
    -------
    freeCitizens : int
        an integer representing the amount of free citizens in the given city.
    """
    freeCitizens = re.search(r'js_GlobalMenu_citizens">(.*?)</span>', html).group(1)
    return parse_int(freeCitizens)

def getPopulation(html):
    """This function is used in the ``getCity`` function to determine the population in the given city.
    Parameters
    ----------
    html : str
        a string representing html which is returned when sending a get request to view a city.

    Returns
    -------
    population : int
        an integer representing the amount of population in the given city.
    """
    population = re.search(r'js_GlobalMenu_population">(.*?)</span>', html).group(1)
    return parse_int(population)


def getResourcesListedForSale(html):
    """This function is used in the ``getCity`` function to determine the amount of each resource which is listed for sale in the branch office
    Parameters
    ----------
    html : str
        a string representing html which is returned when sending a get request to view a city.

    Returns
    -------
    onSale : list[int]
        a list containing 5 integers each of which representing the amount of that particular resource which is on sale in the given city. For more information about the order of the resources, refer to ``config.py``
    """
    rta = re.search(r'branchOfficeResources: JSON\.parse\(\'{\\"resource\\":\\"(\d+)\\",\\"1\\":\\"(\d+)\\",\\"2\\":\\"(\d+)\\",\\"3\\":\\"(\d+)\\",\\"4\\":\\"(\d+)\\"}\'\)', html)
    if rta:
        return [int(rta.group(1)), int(rta.group(2)), int(rta.group(3)), int(rta.group(4)), int(rta.group(5))]
    else:
        return [0, 0, 0, 0, 0]


def format_points(num):
    if num >= 1000000000:
        return str(num // 1000000000) + "kkk"
    elif num >= 1000000:
        return str(num // 1000000) + "kk"
    elif num >= 1000:
        return str(num // 1000) + "k"
    else:
        return str(num)


def populate_island_city(island: dict, city: dict):
    if city['type'] != 'city':
        return

    city['islandX'] = island['x']
    city['islandY'] = island['y']
    city['tradegood'] = island['tradegood']
    city['material'] = materials_names[island['tradegood']]
    city['islandName'] = island['name']
    city['cityName'] = decodeUnicodeEscape(city['name'])
    city['ownerName'] = decodeUnicodeEscape(city['ownerName'])
    city['isNoob'] = city.get('state', '') == 'noob'
    if city['ownerAllyId'] > 0:
        city['allianceName'] = decodeUnicodeEscape(city['ownerAllyTag'])
        city['hasAlliance'] = True
        city['player'] = "{} [{}]".format(city['ownerName'], city['allianceName'])
    else:
        city['alliance'] = ''
        city['hasAlliance'] = False
        city['player'] = city['ownerName']

    _stats = []
    if city['isNoob']:
        _stats.append('noob')

    if 'avatarScores' in island and str(city['ownerId']) in island['avatarScores']:
        _ranking = island['avatarScores'][str(city['ownerId'])]
        city['playerRanking'] = _ranking
        city['playerPlace'] = _ranking['place']
        city['playerPointsWithoutCitizens'] = sum(ceil(parse_int(x) / 100) for x in [
            _ranking['building_score_main'],
            _ranking['research_score_main'],
            _ranking['army_score_main'],
        ])
        _stats.append('#' + str(city['playerPlace']))
        _stats.append('>' + format_points(city['playerPointsWithoutCitizens']))

    city['player'] = "{} ({})".format(city['player'], ", ".join(_stats))


def getIsland(html):
    """This function uses the html passed to it as a string to extract, parse and return an Island object
    Parameters
    ----------
    html : str
        the html returned when a get request to view the island is made. This request can be made with the following statement: ``s.get(urlIsla + islandId)``, where ``urlIsla`` is a string defined in ``config.py`` and ``islandId`` is the id of the island.

    Returns
    -------
    island : Island
        this function returns a json parsed Island object. For more information about this object refer to the github wiki page of Ikabot.
    """
    try:
        # Find the start of the island data object
        marker = 'updateBackgroundData",'
        start_index = html.find(marker)
        if start_index == -1:
            marker = 'updateBackgroundData", '
            start_index = html.find(marker)
            
        if start_index == -1:
            with open('island_error.html', 'w', encoding='utf-8') as f:
                f.write(html)
            raise ValueError("Failed to find updateBackgroundData in island HTML")

        start_index += len(marker)
        while start_index < len(html) and html[start_index] != '{':
            start_index += 1
            
        if start_index >= len(html):
            raise ValueError("Found marker but no JSON object starts after it")

        isla, end_offset = json.JSONDecoder().raw_decode(html[start_index:])
        
    except Exception:
        with open('island_error.html', 'w', encoding='utf-8') as f:
            f.write(html)
        raise

    isla['tipo'] = re.search(r'"tradegood":(\d)', html).group(1)
    isla['x'] = int(isla['xCoord'])
    isla['y'] = int(isla['yCoord'])
    isla['name'] = decodeUnicodeEscape(isla['name'])
    isla['wonderName'] = decodeUnicodeEscape(isla['wonderName'])

    for city in isla['cities']:
        populate_island_city(isla, city)

    return isla


def getCity(html):
    """This function uses the ``html`` passed to it as a string to extract, parse and return a City object
    Parameters
    ----------
    html : str
        the html returned when a get request to view the city is made. This request can be made with the following statement: ``s.get(urlCiudad + id)``, where urlCiudad is a string defined in ``config.py`` and id is the id of the city.

    Returns
    -------
    city : dict
        this function returns a json parsed City object. For more information about this object refer to the github wiki page of Ikabot.
    """

    city = re.search(r'"updateBackgroundData",\s?([\s\S]*?)\],\["updateTemplateData"', html).group(1)
    city = json.loads(city, strict=False)

    city['ownerName'] = decodeUnicodeEscape(city.pop('ownerName'))
    city['x'] = int(city['islandXCoord'])
    city['y'] = int(city['islandYCoord'])
    city['name'] = decodeUnicodeEscape(city['name'])
    city['cityName'] = city['name']

    for building_position, building in enumerate(city['position']):
        building['position'] = building_position
        if 'name' in building and building['name']:
            building['name'] = decodeUnicodeEscape(building['name'])
        if 'level' in building:
            building['level'] = int(building['level'])
        building['isBusy'] = False
        if 'constructionSite' in building['building']:
            building['isBusy'] = True
            building['building'] = building['building'][:-17]
        elif 'buildingGround ' in building['building']:
            building['name'] = 'empty'
            building['type'] = building['building'].split(' ')[-1]
            building['building'] = 'empty'

        building['name'] = decodeUnicodeEscape(building['name'])
        building['positionAndName'] = "[#{}] {}".format(building['position'], building['name'])

    city['id'] = str(city['id'])
    city['isOwnCity'] = True
    city['availableResources'] = getAvailableResources(html, num=True)
    city['storageCapacity'] = getWarehouseCapacity(html)
    city['freeCitizens'] = getFreeCitizens(html)
    city['population'] = getPopulation(html)
    city['wineConsumptionPerHour'] = getWineConsumptionPerHour(html)
    city['resourcesListedForSale'] = getResourcesListedForSale(html)
    city['freeSpaceForResources'] = []
    for i in range(5):
        city['freeSpaceForResources'].append(city['storageCapacity'] - city['availableResources'][i] - city['resourcesListedForSale'][i])

    city['producedTradegood'] = extract_tradegood(html)
    city['tradegood'] = city['producedTradegood']
    city['tradegoodProductionPerSecond'] = extract_tradegood_production(html)
    city['resourceProductionPerSeconds'] = extract_resource_production(html)

    production_per_second = [0] * len(city['availableResources'])
    production_per_second[0] = city['resourceProductionPerSeconds']
    if city['producedTradegood'] is not None:
        production_per_second[city['producedTradegood']] = city['tradegoodProductionPerSecond']

    city['productionPerSecond'] = production_per_second
    city['productionPerHour'] = [int(r*SECONDS_IN_HOUR) for r in production_per_second]

    return city
