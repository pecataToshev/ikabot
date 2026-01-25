#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

from bs4 import BeautifulSoup

from ikabot.config import actionRequest, city_url
from ikabot.helpers.citiesAndIslands import getCityWithCache, getIdsOfCities


def choose_commercial_city(ikariam_service, prompt='Select city with branch office'):
    """
    Prompts the user to select from cities that have a branch office (market).
    Only shows cities with the building, not all cities.
    Uses cached city data (valid for 5 minutes) to reduce HTTP requests.
    Calculates market range using the formula: ceil(building_level / 2).
    
    Parameters
    ----------
    ikariam_service : IkariamService
        Session object
    prompt : str
        The prompt message to display when selecting a city
    
    Returns
    -------
    city : dict
        Selected city with 'marketPosition' and 'rango' fields added
    
    Raises
    ------
    ExitFromMenu
        If user selects exit (option 0) or no cities have a branch office
    """
    from math import ceil
    from ikabot.helpers.gui import enter, select_city_from_list
    from ikabot.helpers.menuExceptions import ExitFromMenu
    
    (cities_ids, _) = getIdsOfCities(ikariam_service)
    commercial_cities = []
    
    print('Loading cities', end='', flush=True)
    for city_id in cities_ids:
        # Use cached city data to reduce requests
        city = getCityWithCache(ikariam_service, city_id)
        for building in city['position']:
            if building['building'] == 'branchOffice':
                city['marketPosition'] = building['position']
                # Calculate range using formula: ceil(building_level / 2)
                city['rango'] = ceil(building['level'] / 2)
                commercial_cities.append(city)
                break
    print(' Done!')
    print()
    
    if len(commercial_cities) == 0:
        print('There is no branch office built in any city!')
        enter()
        raise ExitFromMenu()
    
    # If only one city, return it directly
    if len(commercial_cities) == 1:
        return commercial_cities[0]
    
    # Let user select from cities with branch office
    return select_city_from_list(commercial_cities, prompt=prompt)


def storageCapacityOfMarket(html):
    match = re.search(r'var\s*storageCapacity\s*=\s*(\d+);', html)
    if match:
        return int(match.group(1))
    else:
        return 0


def onSellInMarket(html):
    mad, vin, mar, cri, azu = re.findall(r'<input type="text" class="textfield"\s*size="\d+"\s*name=".*?"\s*id=".*?"\s*value="(\d+)"', html)
    return [int(mad), int(vin), int(mar), int(cri), int(azu)]


def getFinances(session, city_id):
    """
    Get json of finances screen

    :param session : ikabot.web.session.Session
    :param city_id : int
    :return json
    """
    url = 'view=finances&backgroundView=city&currentCityId={}&templateView=finances&actionRequest={}&ajax=1'.format(city_id, actionRequest)
    data = session.post(url)
    return json.loads(data, strict=False)


def getGold(session, city_id):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    city_id : int
    Returns
    -------
    gold : int
    """
    json_data = getFinances(session, city_id)
    gold = json_data[0][1]['headerData']['gold']
    gold = gold.split('.')[0]
    gold = int(gold)
    gold_production = json_data[0][1]['headerData']['scientistsUpkeep'] + json_data[0][1]['headerData']['income'] + json_data[0][1]['headerData']['upkeep']
    return gold, int(gold_production)


def print_table(html_table):
    for row in html_table.find_all('tr'):
        fmt = "{: >30}"
        cells = []
        for cell in row.find_all(['th', 'td']):
            cells.append(fmt.format(cell.get_text(strip=True)))
            fmt = "{: >15}"
        print(" | ".join(cells))


def printGoldForAllCities(session, city_id):
    """
    Prints all the tables from finances for all cities

    :param session : ikabot.web.session.Session
    :param city_id : int
    """
    json_data = getFinances(session, city_id)
    html_code = json_data[1][1][1] # changeView -> finances
    soup = BeautifulSoup(html_code, 'html.parser')
    html_tables = soup.find_all('table')


    # Print each table in a readable format
    for html_table in html_tables:
        print_table(html_table)
        print('-' * 85)  # Add a separator between tables


def getMarketInfo(session, city):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    city : dict

    Returns
    -------
    response : dict
    """
    params = {'view': 'branchOfficeOwnOffers', 'activeTab': 'tab_branchOfficeOwnOffers', 'cityId': city['id'],
              'position': city['marketPosition'], 'backgroundView': 'city', 'currentCityId': city['id'],
              'templateView': 'branchOfficeOwnOffers', 'currentTab': 'tab_branchOfficeOwnOffers',
              'actionRequest': actionRequest, 'ajax': '1'}
    resp = session.post(params=params, noIndex=True)
    return json.loads(resp, strict=False)[1][1][1]


def execute_market_offer_transfer(session, city_id, destination_city_id, market_position,
                                  function_name,  # 'buyGoodsAtAnotherBranchOffice' or 'sellGoodsAtAnotherBranchOffice'
                                  resource_type, amount, price,
                                  ships_available, ships_used,
                                  other_player_name, other_city_name,
                                  offer_type,
                                  action_request):
    """
    Executes a buy or sell transaction at the market (Branch Office).
    Constructs the payload with the specific order of fields required by the server.
    """
    
    # 1. Base Core Data
    data = {
        'action': 'transportOperations',
        'function': function_name,
        'cityId': city_id,
        'destinationCityId': destination_city_id,
        'oldView': 'branchOffice',
        'position': market_position,
        'avatar2Name': other_player_name,
        'city2Name': other_city_name,
        'type': offer_type,
        'activeTab': 'bargain',
        'transportDisplayPrice': '0',
        'premiumTransporter': '0',
        'normalTransportersMax': ships_available,
    }

    # 2. Resource/Price Data
    # Handle resource_type (can be 'resource', 0, or integers 1-4)
    is_resource = str(resource_type) == '0' or str(resource_type) == 'resource'
    
    if is_resource:
        data['resourcePrice'] = price
        data['cargo_resource'] = amount
    else:
        # For tradegoods (1-4)
        r_type_int = int(resource_type)
        data['tradegood{:d}Price'.format(r_type_int)] = price
        data['cargo_tradegood{:d}'.format(r_type_int)] = amount

    # 3. Tail Data
    data.update({
        'capacity': '5',
        'max_capacity': '5',
        'jetPropulsion': '0',
        'transporters': str(ships_used),
        'backgroundView': 'city',
        'currentCityId': city_id,
        'templateView': 'takeOffer',
        'currentTab': 'bargain',
        'actionRequest': action_request,
        'ajax': '1'
    })

    # Execute Request
    return session.post(params=data)

