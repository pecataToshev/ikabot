#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import time

from ikabot.config import MAXIMUM_CITY_NAME_LENGTH, city_url, island_url
from ikabot.helpers.getJson import getCity, getIsland
from ikabot.helpers.gui import (banner, decodeUnicodeEscape, enter,
                                format_city_name, select_city_from_list,
                                select_option_from_list)
from ikabot.helpers.menuExceptions import ExitFromMenu
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService

ids_cache = None
cities_cache = None

# Cache for full city data (including buildings)
# Structure: {city_id: {'data': city_object, 'timestamp': time}}
full_city_cache = {}
CITY_CACHE_TTL = 5 * 60  # 5 minutes in seconds


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
    
    Raises
    ------
    ExitFromMenu
        If user selects exit (option 0)
    """
    (ids, cities) = getIdsOfCities(ikariam_service)
    
    # Special handling for foreign city option
    if foreign:
        # Prepare city list with formatted display
        longest_city_name_length = max([len(decodeUnicodeEscape(cities[city_id]['name'])) for city_id in ids])
        
        def format_city(city_id):
            city_name = decodeUnicodeEscape(cities[city_id]['name'])
            tradegood = cities[city_id]['tradegood']
            return format_city_name(city_name, tradegood, max_length=longest_city_name_length)
        
        print('Select city:\n')
        print('   0: Foreign city')
        for idx, city_id in enumerate(ids, 1):
            print('{:>4}: {}'.format(idx, format_city(city_id)))
        print()
        selected_city_index = read(min=0, max=len(ids), digit=True)
        
        if selected_city_index == 0:
            return chooseForeignCity(ikariam_service)
        else:
            html = ikariam_service.get(city_url + ids[selected_city_index - 1])
            return getCity(html)
    else:
        # Use the standard city selection (raises ExitFromMenu if user exits)
        cities_list = [cities[city_id] for city_id in ids]
        selected_idx = select_city_from_list(
            cities_list,
            prompt='Select city',
            return_index=True
        )
        
        html = ikariam_service.get(city_url + ids[selected_idx])
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

    city_options = []
    for city in island['cities']:
        if city['type'] == 'city' and city['state'] == '' and city['ownerName'] != session.username:
            city_options.append(city)
    
    if len(city_options) == 0:
        print('There are no cities where to send resources on this island')
        enter()
        return chooseCity(session, foreign=True)
    
    # This will raise ExitFromMenu if user selects 0
    city = select_option_from_list(
        city_options,
        prompt='Select foreign city',
        formatter=lambda c: '{: <{max_len}} ({})'.format(
            decodeUnicodeEscape(c['name']),
            decodeUnicodeEscape(c['Name']),
            max_len=MAXIMUM_CITY_NAME_LENGTH
        )
    )
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
        match = re.search(r'relatedCityData:\sJSON\.parse\(\'(.+?),\\"additionalInfo', html)
        if not match:
            dump_file = '/tmp/ikabot_html_dump.txt'
            try:
                with open(dump_file, 'w', encoding='utf-8') as f:
                    f.write(html)
            except Exception:
                pass
            url_base = getattr(ikariam_service, 'urlBase', 'unknown')
            proxies = getattr(ikariam_service.s, 'proxies', {}) if hasattr(ikariam_service, 's') else {}
            raise Exception(f"Cannot parse relatedCityData. HTML saved to {dump_file}. URL: {url_base}, Proxies: {proxies}")
        cities_cache = match.group(1) + '}'
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


def getCityWithCache(ikariam_service: IkariamService, city_id: str, use_cache: bool = True):
    """
    Gets city data with optional caching to reduce HTTP requests.
    Cache is valid for 5 minutes.
    Always shows a progress dot when making HTTP requests.
    
    Parameters
    ----------
    ikariam_service : IkariamService
        Session object
    city_id : str
        The city ID to fetch
    use_cache : bool
        Whether to use cached data (default: True)
    
    Returns
    -------
    city : dict
        City object with building positions
    """
    global full_city_cache
    
    current_time = time.time()
    
    # Check if we should use cache
    if use_cache and city_id in full_city_cache:
        cached_entry = full_city_cache[city_id]
        age = current_time - cached_entry['timestamp']
        
        # Return cached data if it's less than 5 minutes old (no progress indicator)
        if age < CITY_CACHE_TTL:
            return cached_entry['data']
    
    # Fetch fresh data - show progress dot for HTTP request
    print('.', end='', flush=True)
    html = ikariam_service.get(city_url + str(city_id))
    city = getCity(html)
    
    # Store in cache
    full_city_cache[city_id] = {
        'data': city,
        'timestamp': current_time
    }
    
    return city


def clearCityCache():
    """
    Clears the full city data cache.
    Useful when you know city data has changed (e.g., after building upgrade).
    """
    global full_city_cache
    full_city_cache = {}
