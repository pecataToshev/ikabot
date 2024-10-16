#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

from ikabot.config import city_url, island_url, MAXIMUM_CITY_NAME_LENGTH
from ikabot.helpers.getJson import getCity, getIsland
from ikabot.helpers.gui import banner, decodeUnicodeEscape, enter
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService

menu_cities = ''
ids_cache = None
cities_cache = None


def chooseCity(ikariam_service: IkariamService, foreign=False):
    """Prompts the user to chose a city
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
        Session object
    foreign : bool
        lets the user choose a foreign city

    Returns
    -------
    city : City
        a city object representing the chosen city
    """
    global menu_cities
    (ids, cities) = getIdsOfCities(ikariam_service)
    if menu_cities == '':
        longest_city_name_length: int = max([len(decodeUnicodeEscape(cities[city_id]['name'])) for city_id in ids])

        def pad(city_name):
            return ' ' * (longest_city_name_length - len(city_name) + 2)

        resources_abbreviations = {'1': '(W)', '2': '(M)', '3': '(C)', '4': '(S)'}

        i = 0
        if foreign:
            print(' 0: foreign city')
        else:
            print('')
        for city_id in ids:
            i += 1
            resource_index = str(cities[city_id]['tradegood'])
            resource_abb = resources_abbreviations[resource_index]
            city_name = decodeUnicodeEscape(cities[city_id]['name'])
            menu_cities += '{: >2}: {}{}{}\n'.format(i, city_name, pad(city_name), resource_abb)
        menu_cities = menu_cities[:-1]
    if foreign:
        print(' 0: foreign city')
    print(menu_cities)

    if foreign:
        selected_city_index = read(min=0, max=len(ids))
    else:
        selected_city_index = read(min=1, max=len(ids))
    if selected_city_index == 0:
        return chooseForeignCity(ikariam_service)
    else:
        html = ikariam_service.get(city_url + ids[selected_city_index - 1])
        return getCity(html)


def chooseForeignCity(session):
    """Prompts the user to select an island, and a city on that island (is only used in chooseCity)
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
        Session object

    Returns
    -------
    city : City
        a city object representing the city the user chose
    """
    banner()
    x = read(msg='coordinate x:', digit=True)
    y = read(msg='coordinate y:', digit=True)
    print('')
    url = 'view=worldmap_iso&islandX={}&islandY={}&oldBackgroundView=island&islandWorldviewScale=1'.format(x, y)
    html = session.get(url)
    try:
        islands_json = re.search(r'jsonData = \'(.*?)\';', html).group(1)
        islands_json = json.loads(islands_json, strict=False)
        island_id = islands_json['data'][str(x)][str(y)][0]
    except Exception:
        print('Incorrect coordinates')
        enter()
        banner()
        return chooseCity(session, foreign=True)
    html = session.get(island_url + island_id)
    island = getIsland(html)

    i = 0
    city_options = []
    for city in island['cities']:
        if city['type'] == 'city' and city['state'] == '' and city['ownerName'] != session.username:
            i += 1
            num = ' ' + str(i) if i < 10 else str(i)
            print('{: >2}: {: >{max_city_name_length}} ({})'.format(num, decodeUnicodeEscape(city['name']), decodeUnicodeEscape(city['Name']), max_city_name_length=MAXIMUM_CITY_NAME_LENGTH))
            city_options.append(city)
    if i == 0:
        print('There are no cities where to send resources on this island')
        enter()
        return chooseCity(session, foreign=True)
    selected_city_index = read(min=1, max=i)
    city = city_options[selected_city_index - 1]
    city['islandId'] = island['id']
    city['cityName'] = decodeUnicodeEscape(city['name'])
    city['isOwnCity'] = False
    return city


def getIdsOfCities(ikariam_service, all=False):
    """Gets the user's cities
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
        Session object
    all : bool
        boolean indicating whether all cities should be returned, or only those that belong to the current user

    Returns
    -------
    (ids, cities) : tuple
        a tuple containing the list of city IDs and a list of city objects
    """
    global cities_cache
    global ids_cache
    if ids_cache is None or cities_cache is None or ikariam_service.padre is False:
        html = ikariam_service.get()
        cities_cache = re.search(r'relatedCityData:\sJSON\.parse\(\'(.+?),\\"additionalInfo', html).group(1) + '}'
        cities_cache = cities_cache.replace('\\', '')
        cities_cache = cities_cache.replace('city_', '')
        cities_cache = json.loads(cities_cache, strict=False)

        ids_cache = [city_id for city_id in cities_cache]
        ids_cache = sorted(ids_cache)

    # {'coords': '[x:y] ', 'id': idCiudad, 'tradegood': '..', 'name': 'nomberCiudad', 'relationship': 'ownCity'|'occupiedCities'|..}
    if all is False:
        ids_own = [city_id for city_id in cities_cache if cities_cache[city_id]['relationship'] == 'ownCity']
        ids_other = [city_id for city_id in cities_cache if cities_cache[city_id]['relationship'] != 'ownCity']
        own_cities = cities_cache.copy()
        for id in ids_other:
            del own_cities[id]
        return ids_own, own_cities
    else:
        return ids_cache, cities_cache


def getIslandsIds(session):
    """Gets the IDs of islands the user has cities on
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
        Session object

    Returns
    -------
    islands_ids : list
        a list containing the IDs of the users islands
    """
    (cities_ids, cities) = getIdsOfCities(session)
    islands_ids = set()
    for city_id in cities_ids:
        html = session.get(city_url + city_id)
        city = getCity(html)
        island_id = city['islandId']
        islands_ids.add(island_id)
    return list(islands_ids)


def getCurrentCityId(session):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    """
    html = session.get()
    return re.search(r'currentCityId:\s(\d+),', html).group(1)
