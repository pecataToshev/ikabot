#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json

from ikabot.bot.activateMiracleBot import ActivateMiracleBot
from ikabot.config import actionRequest, city_url, island_url
from ikabot.helpers.getJson import getCity, getIsland
from ikabot.helpers.gui import banner, daysHoursMinutes, enter
from ikabot.helpers.citiesAndIslands import getIdsOfCities, getIslandsIds
from ikabot.helpers.userInput import read


def obtainMiraclesAvailable(session):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService

    Returns
    -------
    islands: list[dict]
    """
    idsIslands = getIslandsIds(session)
    islands = []
    for idIsland in idsIslands:
        html = session.get(island_url + idIsland)
        island = getIsland(html)
        island['activable'] = False
        islands.append(island)

    ids, cities = getIdsOfCities(session)
    for city_id in cities:
        city = cities[city_id]
        # get the wonder for this city
        wonder = [island['wonder'] for island in islands if city['coords'] == '[{}:{}] '.format(island['x'], island['y'])][0]
        # if the wonder is not new, continue
        if wonder in [island['wonder'] for island in islands if island['activable']]:
            continue

        html = session.get(city_url + str(city['id']))
        city = getCity(html)

        # make sure that the city has a temple
        for i in range(len(city['position'])):
            if city['position'][i]['building'] == 'temple':
                city['pos'] = str(i)
                break
        else:
            continue

        # get wonder information
        params = {"view": "temple", "cityId": city['id'], "position": city['pos'], "backgroundView": "city", "currentCityId": city['id'], "actionRequest": actionRequest, "ajax": "1"}
        data = session.post(params=params)
        data = json.loads(data, strict=False)
        data = data[2][1]
        available = data['js_WonderViewButton']['buttonState'] == 'enabled'
        if available is False:
            for elem in data:
                if 'countdown' in data[elem]:
                    enddate = data[elem]['countdown']['enddate']
                    currentdate = data[elem]['countdown']['currentdate']
                    break

        # set the information on the island which wonder we can activate
        for island in islands:
            if island['id'] == city['islandId']:
                island['activable'] = True
                island['ciudad'] = city
                island['available'] = available
                if available is False:
                    island['available_in'] = enddate - currentdate
                break

    # only return island which wonder we can activate
    return [island for island in islands if island['activable']]


def chooseIsland(islands):
    """
    Parameters
    ----------
    islands : list[dict]

    Returns
    -------
    island : dict
    """
    print('Which miracle do you want to activate?')
    # Sort islands by name
    sorted_islands = sorted(islands, key=lambda x: x['wonderName'])
    i = 0
    print('(0) Exit')
    for island in sorted_islands:
        i += 1
        if island['available']:
            print('({:d}) {}'.format(i, island['wonderName']))
        else:
            print('({:d}) {} (available in: {})'.format(i, island['wonderName'], daysHoursMinutes(island['available_in'])))

    index = read(min=0, max=i)
    if index == 0:
        return None
    island = sorted_islands[index - 1]
    return island


def activate_miracle_bot_configurator(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()

    islands = obtainMiraclesAvailable(ikariam_service)
    if len(islands) == 0:
        print('There are no miracles available.')
        enter()
        return

    island = chooseIsland(islands)
    if island is None:
        print('No island was chosen. Aborting!')
        enter()
        return

    target_activation_number = read(
        digit=True,
        min=1,
        msg='How many times do yuo want to activate the miracle {} on {}?: '.format(island['wonderName'],
                                                                                    island['id'])
    )

    ActivateMiracleBot(
        ikariam_service=ikariam_service,
        bot_config={
            'targetActivationNumber': target_activation_number,
            'island': island
        }
    ).start(
        action='Activate Miracle',
        objective='{}x{} @ {}'.format(target_activation_number, island['wonderName'], island['id']),
    )
