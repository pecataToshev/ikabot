#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

from ikabot.bot.sellResourcesBot import (SellResourcesToOfferBot,
                                         SellResourcesWithOwnOfferBot)
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import parse_int
from ikabot.helpers.gui import (Colours, addThousandSeparator, banner,
                                decodeUnicodeEscape, enter, format_city_name,
                                printTable)
from ikabot.helpers.market import (choose_commercial_city, getMarketInfo,
                                   storageCapacityOfMarket)
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.web.ikariamService import IkariamService


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
    
    all_offers = []
    offset = 0
    page_num = 1
    
    while True:
        # Build params dictionary - matches the game's actual request
        data = {
            'cityId': my_market_city['id'], 
            'position': my_market_city['marketPosition'], 
            'view': 'branchOffice',
            'activeTab': 'bargain',
            'type': '333', 
            'searchResource': resource_type,
            'range': my_market_city['rango'],
            'backgroundView': 'city', 
            'currentCityId': my_market_city['id'],
            'templateView': 'branchOffice',
            'currentTab': 'bargain',
            'offset': offset,
            'actionRequest': actionRequest, 
            'ajax': '1'
        }
        
        # Show loading message for pages after the first
        if page_num > 1:
            print('Loading offers page {}...'.format(page_num))
        
        # Use POST with params dictionary
        resp = session.post(params=data)
        
        # Check if response is valid JSON
        if not resp or resp.strip() == '':
            break
            
        html = json.loads(resp, strict=False)[1][1][1]

        # Taken from #306
        html_cleaned = re.sub(r'\s+', ' ', html).strip()
        page_offers = re.findall(r'<td class="short_text80">(.*?)<br/>\((.*?)\).*?tooltip">([\d\s.,]+)</div>.*?<td style="white-space:nowrap;">(\d+).*?<td>(\d+)</td>.*?href="\?view=takeOffer&destinationCityId=(\d+)', html_cleaned)
        page_offers = [(cityname.strip(), username.strip(), parse_int(re.sub(r"\s+", "", amount)), parse_int(price), dist, destination_city_id) for cityname, username, amount, price, dist, destination_city_id in page_offers]
        
        all_offers.extend(page_offers)
        
        # If we got no offers on this page, we're done
        if len(page_offers) == 0:
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


def sellToOffers(ikariam_service: IkariamService, city_to_buy_from, resource_type):
    banner()

    offers = getOffers(ikariam_service, city_to_buy_from, resource_type)
    
    if len(offers) == 0:
        print('No offers available.')
        enter()
        return

    # Display current city info
    city_display = format_city_name(
        decodeUnicodeEscape(city_to_buy_from['name']),
        city_to_buy_from['tradegood']
    )
    available = int(city_to_buy_from['availableResources'][resource_type])
    resource_name = materials_names[resource_type]
    
    print('Selling from: {}'.format(city_display))
    print('Available {}: {}'.format(resource_name, addThousandSeparator(available)))
    print('\nAvailable offers to sell to:')
    print('0) Exit\n')
    
    # Convert offers to list of dicts for printTable
    table_data = []
    for idx, offer in enumerate(offers, 1):
        cityname, username, amount, price, dist, destination_city_id = offer
        table_data.append({
            'id': idx,
            'city': cityname.strip(),
            'player': username,
            'amount': amount,
            'price': price,
            'total': price * amount,
            'distance': dist
        })
    
    # Configure table columns
    table_config = [
        {'key': 'id', 'title': 'ID', 'align': '>'},
        {'key': 'city', 'title': 'City', 'align': '<'},
        {'key': 'player', 'title': 'Player', 'align': '<'},
        {'key': 'amount', 'title': 'Amount', 'align': '>', 'fmt': lambda x: addThousandSeparator(x) if x != '' else ''},
        {'key': 'price', 'title': 'Price', 'align': '>'},
        {'key': 'total', 'title': 'Total Gold', 'align': '>', 'fmt': lambda x: addThousandSeparator(x) if x != '' else ''},
        {'key': 'distance', 'title': 'Distance', 'align': '>'}
    ]
    
    printTable(table_config, table_data, print_row_separator=lambda i: i == 0)
    
    print('\nSelect offers to sell to (e.g., "1,3,5" or "all" for all offers):')
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
    total_amount = sum(amount for _, _, amount, _, _, _ in chosen_offers)
    profit = sum(amount * price for _, _, amount, price, _, _ in chosen_offers)

    available = city_to_buy_from['availableResources'][resource_type]
    amount_to_sell = min(available, total_amount)

    banner()
    print('Selected {} offers:'.format(len(chosen_offers)))
    
    # Convert selected offers to list of dicts for printTable
    selected_table_data = []
    for cityname, username, amount, price, dist, destination_city_id in chosen_offers:
        selected_table_data.append({
            'city': cityname.strip(),
            'player': username,
            'amount': amount,
            'price': price,
            'total': price * amount
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
    
    print('Total demand: {}'.format(addThousandSeparator(total_amount)))
    print('Available to sell: {}'.format(addThousandSeparator(available)))
    print('Maximum profit: {}'.format(addThousandSeparator(profit)))
    print('\nHow much do you want to sell? [max = {}]'.format(addThousandSeparator(amount_to_sell)))
    amount_to_sell = read(min=0, max=amount_to_sell)
    if amount_to_sell == 0:
        return

    left_to_sell = amount_to_sell
    profit = 0
    for offer in chosen_offers:
        cityname, username, amount, price, dist, destination_city_id = offer
        sell = min(amount, left_to_sell)
        left_to_sell -= sell
        profit += sell * price

    if not askUserYesNo('Sell {} of {} for a total of {}'.format(addThousandSeparator(amount_to_sell),
                                                                 materials_names[resource_type],
                                                                 addThousandSeparator(profit))):
        return

    SellResourcesToOfferBot(
        ikariam_service=ikariam_service,
        bot_config={
            'left_to_sell': left_to_sell,
            'amount_to_sell': amount_to_sell,
            'offers': chosen_offers,
            'resource_type': resource_type,
            'city_to_buy_from': city_to_buy_from,
        }
    ).start(
        action='Sell To Offers',
        objective="{}{} {}".format(Colours.MATERIALS[resource_type], addThousandSeparator(amount_to_sell),
                                   materials_names[resource_type]),
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
        objective="{}{} {}{} @{}".format(Colours.MATERIALS[resource_type], addThousandSeparator(amount_to_sell),
                                         materials_names[resource_type], Colours.Text.RESET, price),
        target_city=my_offering_market_city['name'],
    )


def sell_resources_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    # Choose city with branch office (handles error if none exist)
    city = choose_commercial_city(ikariam_service, prompt='In which city do you want to sell resources')
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
