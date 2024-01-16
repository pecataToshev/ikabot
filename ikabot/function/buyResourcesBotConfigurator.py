#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import re

from ikabot.bot.buyResourcesBot import BuyResourcesBot
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, enter
from ikabot.helpers.market import getCommercialCities, getGold, getMarketHtml
from ikabot.helpers.pedirInfo import askUserYesNo, read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def chooseResource(session, city):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    city : dict
    """
    print('Which resource do you want to buy?')
    for index, material_name in enumerate(materials_names):
        print('({:d}) {}'.format(index+1, material_name))
    choise = read(min=1, max=5)
    resource = choise - 1
    if resource == 0:
        resource = 'resource'
    data = {
        'cityId': city['id'],
        'position': city['marketPosition'],
        'view': 'branchOffice',
        'activeTab': 'bargain',
        'type': 444,
        'searchResource': resource,
        'range': city['rango'],
        'backgroundView': 'city',
        'currentCityId': city['id'],
        'templateView': 'branchOffice',
        'currentTab': 'bargain',
        'actionRequest': actionRequest,
        'ajax': 1
    }
    # this will set the chosen resource in the store
    session.post(params=data)
    resource = choise - 1
    # return the chosen resource
    return resource


def getOffers(session, city):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    city : dict
    Returns
    -------
    offers : list[dict]
    """
    html = getMarketHtml(session, city)
    hits = re.findall(r'short_text80">(.*?) *<br/>\((.*?)\)\s *</td>\s *<td>(\d+)</td>\s *<td>(.*?)/td>\s *<td><img src="(.*?)\.png[\s\S]*?white-space:nowrap;">(\d+)\s[\s\S]*?href="\?view=takeOffer&destinationCityId=(\d+)&oldView=branchOffice&activeTab=bargain&cityId=(\d+)&position=(\d+)&type=(\d+)&resource=(\w+)"', html)
    offers = []
    for hit in hits:
        offer = {
            'ciudadDestino': hit[0],
            'jugadorAComprar': hit[1],
            'bienesXminuto': int(hit[2]),
            'amountAvailable': int(hit[3].replace(',', '').replace('.', '').replace('<', '')),
            'tipo': hit[4],
            'precio': int(hit[5]),
            'destinationCityId': hit[6],
            'cityId': hit[7],
            'position': hit[8],
            'type': hit[9],
            'resource': hit[10]
        }
        
        #Parse CDN Images to material type
        if offer["tipo"] == '//gf2.geo.gfsrv.net/cdn19/c3527b2f694fb882563c04df6d8972':
             offer["tipo"] = 'wood'
        elif offer["tipo"] == '//gf1.geo.gfsrv.net/cdnc6/94ddfda045a8f5ced3397d791fd064':
            offer["tipo"] = 'wine'     
        elif  offer["tipo"] == '//gf3.geo.gfsrv.net/cdnbf/fc258b990c1a2a36c5aeb9872fc08a':
             offer["tipo"] = 'marble'
        elif  offer["tipo"] == '//gf2.geo.gfsrv.net/cdn1e/417b4059940b2ae2680c070a197d8c':
             offer["tipo"] = 'glass'
        elif  offer["tipo"] == '//gf1.geo.gfsrv.net/cdn9b/5578a7dfa3e98124439cca4a387a61':
             offer["tipo"] = 'sulfur'
        else:
            continue
            
        offers.append(offer)
    return offers


def calculateCost(offers, total_amount_to_buy):
    """
    Parameters
    ----------
    offers : list[dict]
    total_amount_to_buy : int
    Returns
    -------
    total_cost : int
    """
    total_cost = 0
    for offer in offers:
        if total_amount_to_buy == 0:
            break
        buy_amount = min(offer['amountAvailable'], total_amount_to_buy)
        total_amount_to_buy -= buy_amount
        total_cost += buy_amount * offer['precio']
    return total_cost


def chooseCommertialCity(commercial_cities):
    """
    Parameters
    ----------
    commercial_cities : list[dict]

    Returns
    -------
    commercial_city : dict
    """
    print('From which city do you want to buy resources?\n')
    for i, city in enumerate(commercial_cities):
        print('({:d}) {}'.format(i + 1, city['name']))
    selected_city_index = read(min=1, max=len(commercial_cities))
    return commercial_cities[selected_city_index - 1]


def buy_resources_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    # get all the cities with a store
    commercial_cities = getCommercialCities(ikariam_service)
    if len(commercial_cities) == 0:
        print('There is no store build')
        enter()
        return

    # choose which city to buy from
    if len(commercial_cities) == 1:
        city = commercial_cities[0]
    else:
        city = chooseCommertialCity(commercial_cities)
        banner()

    # choose resource to buy
    resource = chooseResource(ikariam_service, city)
    banner()

    # get all the offers of the chosen resource from the chosen city
    offers = getOffers(ikariam_service, city)
    if len(offers) == 0:
        print('There are no offers available.')
        enter()
        return

    # display offers to the user
    total_price = 0
    total_amount = 0
    for offer in offers:
        amount = offer['amountAvailable']
        price = offer['precio']
        cost = amount * price
        print('amount:{}'.format(addThousandSeparator(amount)))
        print('price :{:d}'.format(price))
        print('cost  :{}'.format(addThousandSeparator(cost)))
        print('')
        total_price += cost
        total_amount += amount

    # ask how much to buy
    print('Total amount available to purchase: {}, for {}'.format(addThousandSeparator(total_amount), addThousandSeparator(total_price)))
    available = city['freeSpaceForResources'][resource]
    if available < total_amount:
        print('You just can buy {} due to storing capacity'.format(addThousandSeparator(available)))
        total_amount = available
    print('')
    amount_to_buy = read(msg='How much do you want to buy?: ', min=0, max=total_amount)
    if amount_to_buy == 0:
        return

    # calculate the total cost
    (gold, __) = getGold(ikariam_service, city)
    total_cost = calculateCost(offers, amount_to_buy)

    print('\nCurrent gold: {}.\nTotal cost  : {}.\nFinal gold  : {}.'. format(addThousandSeparator(gold), addThousandSeparator(total_cost), addThousandSeparator(gold - total_cost)))
    if not askUserYesNo('Proceed'):
        return

    print('It will be purchased {}'.format(addThousandSeparator(amount_to_buy)))
    enter()

    BuyResourcesBot(
        ikariam_service=ikariam_service,
        bot_config={
            'amountToBuy': amount_to_buy,
            'offers': offers,
            'buildingPosition': city['marketPosition'],
            'resource': resource,
            'cityName': city['name'],
        }
    ).start(
        action='Buy Resources',
        objective='{} {}'.format(addThousandSeparator(amount_to_buy), materials_names[resource]),
        target_city=city['name'],
    )
