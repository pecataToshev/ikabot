#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

from ikabot.bot.market.buyMarketBot import BuyMarketBot
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.database import Database
from ikabot.helpers.gui import (addThousandSeparator, banner,
                                decodeUnicodeEscape, enter, format_city_name,
                                printTable)
from ikabot.helpers.market import choose_commercial_city, getGold
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
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
    all_offers = []
    offset = 0
    page_num = 1
    
    while True:
        # Build params dictionary - matches the game's actual request
        # Note: resource type already set by chooseResource
        params = {
            'cityId': city['id'], 
            'position': city['marketPosition'],
            'view': 'branchOffice', 
            'activeTab': 'bargain',
            'backgroundView': 'city', 
            'currentCityId': city['id'], 
            'templateView': 'branchOffice',
            'offset': offset,  # Always include offset, even when 0
            'actionRequest': actionRequest, 
            'ajax': '1'
        }
        
        # Show loading message for pages after the first
        if page_num > 1:
            print('Loading offers page {}...'.format(page_num))
        
        # Use POST with params dictionary
        data = session.post(params=params)
        
        # Check if response is valid JSON
        if not data or data.strip() == '':
            break
            
        html = json.loads(data, strict=False)[1][1][1]
        html_cleaned = re.sub(r'\s+', ' ', html).strip()

        hits = re.findall(r'short_text80">(.*?) <br/>\((.*?)\).*?<td>(\d+)</td>.*?tooltip">([\d\s.,]+)</div>.*?src="(.*?)\.png".*?white-space:nowrap;">(\d+).*?view=takeOffer&destinationCityId=(\d+)&oldView=branchOffice&activeTab=bargain&cityId=(\d+)&position=(\d+)&type=(\d+)&resource=(\w+)"', html_cleaned)
        
        offers_before = len(all_offers)
        
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
            elif  offer["tipo"] == '//gf2.geo.gfsrv.net/cdn1e\/417b4059940b2ae2680c070a197d8c':
                 offer["tipo"] = 'glass'
            elif  offer["tipo"] == '//gf1.geo.gfsrv.net/cdn9b/5578a7dfa3e98124439cca4a387a61':
                 offer["tipo"] = 'sulfur'
            else:
                continue
                
            all_offers.append(offer)
        
        # If we got no new offers on this page, we're done
        if len(all_offers) == offers_before:
            break
        
        # Check if there's a next page by looking for ALL offset values in pagination links
        all_offsets = re.findall(r'offset=(\d+)', html)
        
        if all_offsets:
            # Convert to integers and find the maximum
            offset_values = [int(o) for o in all_offsets]
            max_offset = max(offset_values)
            
            if max_offset > offset:
                offset = max_offset
                page_num += 1
            else:
                break
        else:
            break
    
    return all_offers


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


def buy_resources_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    # Choose city with branch office (handles error if none exist)
    city = choose_commercial_city(ikariam_service, prompt='From which city do you want to buy resources')
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

    # display current city info
    city_display = format_city_name(
        decodeUnicodeEscape(city['name']),
        city['tradegood']
    )
    free_space = int(city['freeSpaceForResources'][resource])
    resource_name = materials_names[resource]
    
    print('Buying for: {}'.format(city_display))
    print('Free storage for {}: {}'.format(resource_name, addThousandSeparator(free_space)))
    print('\nAvailable offers to buy from:')
    print('0) Exit\n')
    
    # Convert offers to list of dicts for printTable
    table_data = []
    total_price = 0
    total_amount = 0
    
    for idx, offer in enumerate(offers, 1):
        amount = offer['amountAvailable']
        price = offer['precio']
        cost = amount * price
        cityname = offer['ciudadDestino']
        username = offer['jugadorAComprar']
        
        table_data.append({
            'id': idx,
            'city': cityname.strip(),
            'player': username,
            'amount': amount,
            'price': price,
            'total': cost
        })
        
        total_price += cost
        total_amount += amount
    
    # Configure table columns
    table_config = [
        {'key': 'id', 'title': 'ID', 'align': '>'},
        {'key': 'city', 'title': 'City', 'align': '<'},
        {'key': 'player', 'title': 'Player', 'align': '<'},
        {'key': 'amount', 'title': 'Amount', 'align': '>', 'fmt': addThousandSeparator},
        {'key': 'price', 'title': 'Price', 'align': '>'},
        {'key': 'total', 'title': 'Total Gold', 'align': '>', 'fmt': addThousandSeparator}
    ]
    
    printTable(table_config, table_data, print_row_separator=lambda i: i == 0)

    print('\nSelect offers to buy from (e.g., "1,3,5" or "all" for all offers):')
    selection = read(msg='Selection: ', empty=False)

    if selection == '0':
        return

    # Parse selection
    chosen_offers = []
    if selection.lower() == 'all':
        chosen_offers = offers
    else:
        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            chosen_offers = [offers[i-1] for i in indices if 1 <= i <= len(offers)]
        except (ValueError, IndexError):
            print('Invalid selection')
            enter()
            return

    if len(chosen_offers) == 0:
        print('No offers selected')
        enter()
        return

    # Calculate totals for selected offers
    total_amount = sum(offer['amountAvailable'] for offer in chosen_offers)
    total_price = sum(offer['amountAvailable'] * offer['precio'] for offer in chosen_offers)

    banner()
    print('Selected {} offers:'.format(len(chosen_offers)))

    # Convert selected offers to list of dicts for printTable
    selected_table_data = []
    for idx, offer in enumerate(chosen_offers, 1):
        selected_table_data.append({
            'city': offer['ciudadDestino'].strip(),
            'player': offer['jugadorAComprar'],
            'amount': offer['amountAvailable'],
            'price': offer['precio'],
            'total': offer['amountAvailable'] * offer['precio']
        })

    # Configure table columns for selected offers
    selected_table_config = [
        {'key': 'city', 'title': 'City', 'align': '<'},
        {'key': 'player', 'title': 'Player', 'align': '<'},
        {'key': 'amount', 'title': 'Amount', 'align': '>', 'fmt': addThousandSeparator},
        {'key': 'price', 'title': 'Price', 'align': '>'},
        {'key': 'total', 'title': 'Total Gold', 'align': '>', 'fmt': addThousandSeparator}
    ]

    printTable(selected_table_config, selected_table_data, print_row_separator=lambda i: i == 0)

    print('\nTotal demand from selected offers: {}'.format(addThousandSeparator(total_amount)))
    available = city['freeSpaceForResources'][resource]
    if available < total_amount:
        print('You can only buy up to {} due to storage capacity'.format(addThousandSeparator(available)))
        limit_amount = available
    else:
        limit_amount = total_amount

    print('')
    amount_to_buy = read(msg='How much do you want to buy? [max = {}]: '.format(addThousandSeparator(limit_amount)), min=0, max=limit_amount)
    if amount_to_buy == 0:
        return

    # calculate the total cost
    (gold, __) = getGold(ikariam_service, city)
    total_cost = calculateCost(chosen_offers, amount_to_buy)

    if gold > 0:
        print('\nCurrent gold: {}.\nTotal cost  : {}.\nFinal gold  : {}.'. format(addThousandSeparator(gold), addThousandSeparator(total_cost), addThousandSeparator(gold - total_cost)))
    else:
        print('\nTotal cost: {}.'.format(addThousandSeparator(total_cost)))

    if not askUserYesNo('Proceed'):
        return

    print('It will be purchased {}'.format(addThousandSeparator(amount_to_buy)))
    enter()

    BuyMarketBot(
        ikariam_service=ikariam_service,
        bot_config={
            'amountToBuy': amount_to_buy,
            'offers': chosen_offers,
            'buildingPosition': city['marketPosition'],
            'resource': resource,
            'cityName': city['name'],
        }
    ).start(
        action='Buy Resources',
        objective='{} {}'.format(addThousandSeparator(amount_to_buy), materials_names[resource]),
        target_city=city['name'],
    )
