#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot import config
from ikabot.bot.transportGoodsBot import TransportGoodsBot, TransportJob
from ikabot.config import city_url, materials_names
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, enter
from ikabot.helpers.naval import TransportShip, get_transport_ships_size
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.web.ikariamService import IkariamService


def __get_route_text(route: TransportJob, resource: int) -> str:
    return '{:>{maxCityLen}} ---> {:<{maxCityLen}} : {} {}'.format(
        route.origin_city['name'],
        route.target_city['name'],
        materials_names[resource],
        addThousandSeparator(route.resources[resource]),
        maxCityLen=config.MAXIMUM_CITY_NAME_LENGTH
    )


def distribute_resources_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    print('What resource do you want to distribute?')
    print('(0) Exit')
    for i in range(len(materials_names)):
        print('({:d}) {}'.format(i+1, materials_names[i]))
    resource = read(min=0, max=5)
    if resource == 0:
        return
    resource -= 1

    if resource == 0:
        evenly = True
    else:
        print('\nHow do you want to distribute the resources?')
        print('1) From cities that produce them to cities that do not')
        print('2) Distribute them evenly among all cities')
        type_distribution = read(min=1, max=2)
        evenly = type_distribution == 2

    if evenly:
        routes = distribute_evenly(ikariam_service, resource)
    else:
        routes = distribute_unevenly(ikariam_service, resource)

    if routes is None:
        return

    banner()
    print('\nThe following shipments will be made:\n')
    for route in routes:
        print(__get_route_text(route, resource))

    if not askUserYesNo('Execute all routes'):
        route_index_to_remove = []
        for i, route in enumerate(routes):
            if not askUserYesNo('Execute ' + __get_route_text(route, resource)):
                route_index_to_remove.append(i)

        routes = [route for i, route in enumerate(routes) if i not in route_index_to_remove]

    if len(routes) == 0:
        print('No routes to execute')
        enter()
        return

    ship_size = get_transport_ships_size(ikariam_service, routes[0].origin_city['id'], TransportShip.TRANSPORT_SHIP)
    TransportGoodsBot(
        ikariam_service=ikariam_service,
        bot_config={
            'jobs': routes,
            'batchSize': TransportGoodsBot.DEFAULT_NUMBER_OF_SHIPS_IN_BATCH * ship_size,
            'shipSize': ship_size
        }
    ).start(
        action='Distribute Resources',
        objective='Evenly' if evenly else 'From Producers'
    )


def distribute_evenly(session, resource_type):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    resource_type : int
    """
    resourceTotal = 0
    (cityIDs, cities) = getIdsOfCities(session)

    originCities = {}
    destinationCities = {}
    allCities = {}
    for cityID in cityIDs:

        html = session.get(city_url + cityID)  # load html from the get request for that particular city
        city = getCity(html)  # convert the html to a city object

        resourceTotal += city['availableResources'][resource_type]  # the cities resources are added to the total
        allCities[cityID] = city  # adds the city to all cities

    # if a city doesn't have enough storage to fit resourceAverage
    # ikabot will send enough resources to fill the store to the max
    # then, resourceAverage will be recalculated
    resourceAverage = resourceTotal // len(allCities)
    while True:

        len_prev = len(destinationCities)
        for cityID in allCities:
            if cityID in destinationCities:
                continue
            freeStorage = allCities[cityID]['freeSpaceForResources'][resource_type]
            storage = allCities[cityID]['storageCapacity']
            if storage < resourceAverage:
                destinationCities[cityID] = freeStorage
                resourceTotal -= storage

        resourceAverage = resourceTotal // (len(allCities) - len(destinationCities))

        if len_prev == len(destinationCities):
            for cityID in allCities:
                if cityID in destinationCities:
                    continue
                if allCities[cityID]['availableResources'][resource_type] > resourceAverage:
                    originCities[cityID] = allCities[cityID]['availableResources'][resource_type] - resourceAverage
                else:
                    destinationCities[cityID] = resourceAverage - allCities[cityID]['availableResources'][resource_type]
            break

    originCities = {k: v for k, v in sorted(originCities.items(), key=lambda item: item[1], reverse=True)}  # sort origin cities in descending order
    destinationCities = {k: v for k, v in sorted(destinationCities.items(), key=lambda item: item[1])}  # sort destination cities in ascending order

    routes = []

    for originCityID in originCities:  # iterate through all origin city ids

        for destinationCityID in destinationCities:  # iterate through all destination city ids
            if originCities[originCityID] == 0 or destinationCities[destinationCityID] == 0:
                continue

            if originCities[originCityID] > destinationCities[destinationCityID]:  # if there's more resources above average in the origin city than resources below average in the destination city (origin city needs to have a surplus and destination city needs to have a deficit of resources for a route to be considered)
                toSend = destinationCities[destinationCityID]  # number of resources to send is the number of resources below average in destination city
            else:
                toSend = originCities[originCityID]  # send the amount of resources above average of the current origin city

            if toSend == 0:
                continue

            toSendArr = [0] * len(materials_names)
            toSendArr[resource_type] = toSend
            routes.append(TransportJob(
                origin_city=allCities[originCityID],
                target_city=allCities[destinationCityID],
                resources=toSendArr,
            ))

            # ROUTE BLOCK
            if originCities[originCityID] > destinationCities[destinationCityID]:
                originCities[originCityID] -= destinationCities[destinationCityID]  # remove the sent amount from the origin city's surplus
                destinationCities[destinationCityID] = 0  # set the amount of resources below average in destination city to 0
            else:
                destinationCities[destinationCityID] -= originCities[originCityID]  # remove the sent amount from the amount of resources below average in current destination city
                originCities[originCityID] = 0  # set the amount of resources above average in origin city to 0

    return routes


def distribute_unevenly(session, resource_type):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    resource_type : int
    """
    total_available_resources_from_all_cities = 0
    (cities_ids, cities) = getIdsOfCities(session)
    origin_cities = {}
    destination_cities = {}
    for destination_city_id in cities_ids:
        is_city_mining_this_resource = cities[destination_city_id]['tradegood'] == resource_type
        if is_city_mining_this_resource:
            html = session.get(city_url + destination_city_id)
            city = getCity(html)
            if resource_type == 1:  # wine
                city['available_amount_of_resource'] = city['availableResources'][resource_type] - city['wineConsumptionPerHour'] - 1
            else:
                city['available_amount_of_resource'] = city['availableResources'][resource_type]
            if city['available_amount_of_resource'] < 0:
                city['available_amount_of_resource'] = 0
            total_available_resources_from_all_cities += city['available_amount_of_resource']
            origin_cities[destination_city_id] = city
        else:
            html = session.get(city_url + destination_city_id)
            city = getCity(html)
            city['free_storage_for_resource'] = city['freeSpaceForResources'][resource_type]
            if city['free_storage_for_resource'] > 0:
                destination_cities[destination_city_id] = city

    if total_available_resources_from_all_cities <= 0:
        print('\nThere are no resources to send.')
        enter()
        return None
    if len(destination_cities) == 0:
        print('\nThere is no space available to send resources.')
        enter()
        return None

    remaining_resources_to_be_sent_to_each_city = total_available_resources_from_all_cities // len(destination_cities)
    free_storage_available_per_city = [destination_cities[city]['free_storage_for_resource'] for city in destination_cities]
    total_free_storage_available_in_all_cities = sum(free_storage_available_per_city)
    remaining_resources_to_send = min(total_available_resources_from_all_cities, total_free_storage_available_in_all_cities)
    toSend = {}

    while remaining_resources_to_send > 0:
        len_prev = len(toSend)
        for city_id in destination_cities:
            city = destination_cities[city_id]
            if city_id not in toSend and city['free_storage_for_resource'] < remaining_resources_to_be_sent_to_each_city:
                toSend[city_id] = city['free_storage_for_resource']
                remaining_resources_to_send -= city['free_storage_for_resource']

        if len(toSend) == len_prev:
            for city_id in destination_cities:
                if city_id not in toSend:
                    toSend[city_id] = remaining_resources_to_be_sent_to_each_city
            break

        free_storage_available_per_city = [destination_cities[city]['free_storage_for_resource'] for city in destination_cities if city not in toSend]
        if len(free_storage_available_per_city) == 0:
            break
        total_free_storage_available_in_all_cities = sum(free_storage_available_per_city)
        remaining_resources_to_send = min(remaining_resources_to_send, total_free_storage_available_in_all_cities)
        remaining_resources_to_be_sent_to_each_city = remaining_resources_to_send // len(free_storage_available_per_city)

    routes = []
    for destination_city_id in destination_cities:
        destination_city = destination_cities[destination_city_id]
        missing_resources = toSend[destination_city_id]
        for origin_city_id in origin_cities:
            if missing_resources == 0:
                break

            origin_city = origin_cities[origin_city_id]
            resources_available_in_this_city = origin_city['available_amount_of_resource']
            for route in routes:
                if route.origin_city['id'] == origin_city_id:
                    resources_available_in_this_city -= route.resources[resource_type]

            send_this_round = min(missing_resources, resources_available_in_this_city)
            available = destination_city['free_storage_for_resource']
            if available == 0 or send_this_round == 0:
                continue

            if available < send_this_round:
                missing_resources = 0
                send_this_round = available
            else:
                missing_resources -= send_this_round

            toSendArr = [0] * len(materials_names)
            toSendArr[resource_type] = send_this_round

            routes.append(TransportJob(
                origin_city=origin_city,
                target_city=destination_city,
                resources=toSendArr,
            ))

    return routes
