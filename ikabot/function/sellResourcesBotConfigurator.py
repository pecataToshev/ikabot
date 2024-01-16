#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

from ikabot.bot.sellResourcesBot import SellResourcesToOfferBot, SellResourcesWithOwnOfferBot
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, enter
from ikabot.helpers.market import getCommercialCities, storageCapacityOfMarket
from ikabot.helpers.pedirInfo import read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def chooseCommercialCity(commercial_cities):
    """
    Parameters
    ----------
    commercial_cities : list[dict]

    Returns
    -------
    commercial_city : dict
    """
    print('In which city do you want to sell resources?\n')
    for i, city in enumerate(commercial_cities):
        print('({:d}) {}'.format(i + 1, city['name']))
    ind = read(min=1, max=len(commercial_cities))
    return commercial_cities[ind - 1]


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
              'position': city['pos'], 'backgroundView': 'city', 'currentCityId': city['id'],
              'templateView': 'branchOfficeOwnOffers', 'currentTab': 'tab_branchOfficeOwnOffers',
              'actionRequest': actionRequest, 'ajax': '1'}
    resp = session.post(params=params, noIndex=True)
    return json.loads(resp, strict=False)[1][1][1]


def getOffers(session, my_market_city, resource_type):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    my_market_city : dict
    resource_type : int

    Returns
    -------
    offers : list
    """
    if resource_type == 0:
        resource_type = 'resource'
    else:
        resource_type = str(resource_type)
    data = {'cityId': my_market_city['id'], 'position': my_market_city['pos'], 'view': 'branchOffice',
            'activeTab': 'bargain', 'type': '333', 'searchResource': resource_type, 'range': my_market_city['rango'],
            'backgroundView': 'city', 'currentCityId': my_market_city['id'], 'templateView': 'branchOffice',
            'currentTab': 'bargain', 'actionRequest': actionRequest, 'ajax': '1'}
    resp = session.post(params=data)
    html = json.loads(resp, strict=False)[1][1][1]
    return re.findall(
        r'<td class=".*?">(.*?)<br/>\((.*?)\)\s*</td>\s*<td>(.*?)</td>\s*<td><img src=".*?"\s*alt=".*?"\s*title=".*?"/></td>\s*<td style="white-space:nowrap;">(\d+)\s*<img src=".*?"\s*class=".*?"/>.*?</td>\s*<td>(\d+)</td>\s*<td><a onclick="ajaxHandlerCall\(this\.href\);return false;"\s*href="\?view=takeOffer&destinationCityId=(\d+)&',
        html)


def sellToOffers(ikariam_service: IkariamService, city_to_buy_from, resource_type):
    banner()

    offers = getOffers(ikariam_service, city_to_buy_from, resource_type)

    if len(offers) == 0:
        print('No offers available.')
        enter()
        return

    print('Which offers do you want to sell to?\n')

    chosen_offers = []
    total_amount = 0
    profit = 0
    for offer in offers:
        cityname, username, amount, price, dist, destination_city_id = offer
        cityname = cityname.strip()
        amount = amount.replace(',', '').replace('.', '')
        amount = int(amount)
        price = int(price)
        msg = '{} ({}): {} at {:d} each ({} in total) [Y/n]'.format(cityname, username, addThousandSeparator(amount),
                                                                    price, addThousandSeparator(price * amount))
        rta = read(msg=msg, values=['y', 'Y', 'n', 'N', ''])
        if rta.lower() == 'n':
            continue
        chosen_offers.append(offer)
        total_amount += amount
        profit += amount * price

    if len(chosen_offers) == 0:
        return

    available = city_to_buy_from['availableResources'][resource_type]
    amount_to_sell = min(available, total_amount)

    banner()
    print('\nHow much do you want to sell? [max = {}]'.format(addThousandSeparator(amount_to_sell)))
    amount_to_sell = read(min=0, max=amount_to_sell)
    if amount_to_sell == 0:
        return

    left_to_sell = amount_to_sell
    profit = 0
    for offer in chosen_offers:
        cityname, username, amount, price, dist, destination_city_id = offer
        cityname = cityname.strip()
        amount = amount.replace(',', '').replace('.', '')
        amount = int(amount)
        price = int(price)
        sell = min(amount, left_to_sell)
        left_to_sell -= sell
        profit += sell * price
    print('\nSell {} of {} for a total of {}? [Y/n]'.format(addThousandSeparator(amount_to_sell),
                                                            materials_names[resource_type],
                                                            addThousandSeparator(profit)))
    rta = read(values=['y', 'Y', 'n', 'N', ''])
    if rta.lower() == 'n':
        return

    SellResourcesToOfferBot(
        ikariam_service=ikariam_service,
        bot_config={
            'left_to_sell': left_to_sell,
            'amount_to_sell': amount_to_sell,
            'offers': offers,
            'resource_type': resource_type,
            'city_to_buy_from': city_to_buy_from,
        }
    ).start(
        action='Sell To Offers',
        objective='{} {}'.format(addThousandSeparator(amount_to_sell), materials_names[resource_type])
    )


def createOffer(ikariam_service: IkariamService, my_offering_market_city, resource_type):
    banner()

    html = getMarketInfo(ikariam_service, my_offering_market_city)
    sell_market_capacity = storageCapacityOfMarket(html)
    total_available_amount_of_resource = my_offering_market_city['availableResources'][resource_type]

    print('How much do you want to sell? [max = {}]'.format(addThousandSeparator(total_available_amount_of_resource)))
    amount_to_sell = read(min=0, max=total_available_amount_of_resource)
    if amount_to_sell == 0:
        return

    price_max, price_min = re.findall(r'\'upper\': (\d+),\s*\'lower\': (\d+)', html)[resource_type]
    price_max = int(price_max)
    price_min = int(price_min)
    print('\nAt what price? [min = {:d}, max = {:d}]'.format(price_min, price_max))
    price = read(min=price_min, max=price_max)

    print(
        '\nI will sell {} of {} at {}: {}'.format(addThousandSeparator(amount_to_sell), materials_names[resource_type],
                                                  addThousandSeparator(price),
                                                  addThousandSeparator(price * amount_to_sell)))
    print('\nProceed? [Y/n]')
    rta = read(values=['y', 'Y', 'n', 'N', ''])
    if rta.lower() == 'n':
        return

    SellResourcesWithOwnOfferBot(
        ikariam_service=ikariam_service,
        bot_config={
            'amount_to_sell': amount_to_sell,
            'price': price,
            'resource_type': resource_type,
            'sell_market_capacity': sell_market_capacity,
            'my_offering_market_city': my_offering_market_city,

        }
    ).start(
        action="Sell Own Offers",
        objective="{} @{}".format(addThousandSeparator(amount_to_sell), price),
        target_city=my_offering_market_city['name'],
    )


def sell_resources_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    commercial_cities = getCommercialCities(ikariam_service)
    if len(commercial_cities) == 0:
        print('There is no store built')
        enter()
        return

    if len(commercial_cities) == 1:
        city = commercial_cities[0]
    else:
        city = chooseCommercialCity(commercial_cities)
        banner()

    print('What resource do you want to sell?')
    for index, material_name in enumerate(materials_names):
        print('({:d}) {}'.format(index + 1, material_name))
    selected_material = read(min=1, max=len(materials_names))
    resource = selected_material - 1
    banner()

    print('Do you want to sell to existing offers (1) or do you want to make your own offer (2)?')
    selected = read(min=1, max=2)
    [sellToOffers, createOffer][selected - 1](ikariam_service, city, resource)

