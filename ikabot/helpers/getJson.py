#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

from ikabot.config import SECONDS_IN_HOUR
from ikabot.helpers.gui import decodeUnicodeEscape
from ikabot.helpers.resources import extract_resource_production, extract_tradegood, extract_tradegood_production, \
    getAvailableResources, \
    getWarehouseCapacity, \
    getWineConsumptionPerHour


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
    return int(freeCitizens.replace(',', '').replace('.', ''))

def getPopulation(html):
    """This function is used in the ``getCity`` function to determine the population in the given city.
    Parameters
    ----------
    html : str
        a string representing html which is returned when sending a get request to view a city.

    Returns
    -------
    freeCitizens : int
        an integer representing the amount of free citizens in the given city.
    """
    freeCitizens = re.search(r'js_GlobalMenu_population">(.*?)</span>', html).group(1)
    return int(freeCitizens.replace(',', '').replace('.', ''))


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
    isla = re.search(r'\[\["updateBackgroundData",([\s\S]*?),"specialServerBadges', html).group(1) + '}'

    isla = isla.replace('buildplace', 'empty')
    isla = isla.replace('xCoord', 'x')
    isla = isla.replace('yCoord', 'y')
    isla = isla.replace(',"owner', ',"')

    # {"id":idIsla,"name":nombreIsla,"x":,"y":,"good":numeroBien,"woodLv":,"goodLv":,"wonder":numeroWonder, "wonderName": "nombreDelMilagro","wonderLv":"5","cities":[{"type":"city","name":cityName,"id":cityId,"level":lvIntendencia,"Id":playerId,"Name":playerName,"AllyId":,"AllyTag":,"state":"vacation"},...}}
    isla = json.loads(isla, strict=False)
    isla['tipo'] = re.search(r'"tradegood":(\d)', html).group(1)
    isla['x'] = int(isla['x'])
    isla['y'] = int(isla['y'])

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

    city['ownerId'] = city.pop('ownerId')
    city['ownerName'] = decodeUnicodeEscape(city.pop('ownerName'))
    city['x'] = int(city.pop('islandXCoord'))
    city['y'] = int(city.pop('islandYCoord'))
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
    city['productionPerHour'] = [r*SECONDS_IN_HOUR for r in production_per_second]

    return city
