#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import math
import os
import re
import sys
import threading
import time
import traceback
from decimal import Decimal

import requests

from ikabot import config
from ikabot.config import actionRequest, city_url, materials_names, materials_names_tec, \
    MAXIMUM_CITY_NAME_LENGTH
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, bcolors, decodeUnicodeEscape, enter
from ikabot.helpers.pedirInfo import chooseCity, getIdsOfCities, read
from ikabot.helpers.planRoutes import executeRoutes, getMinimumWaitingTime
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal

sendResources = True
expand = True
thread = None

def waitForConstruction(session, city_id):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    city_id : int

    Returns
    -------
    city : dict
    """
    while True:

        html = session.get(city_url + city_id)
        city = getCity(html)

        construction_buildings = [building for building in city['position'] if 'completed' in building]
        if len(construction_buildings) == 0:
            break

        construction_building = construction_buildings[0]
        construction_time = construction_building['completed']

        current_time = int(time.time())
        final_time = int(construction_time)
        seconds_to_wait = final_time - current_time

        msg = 'I wait {} to get to level {:d}'.format(construction_building['name'],
                                                      construction_building['level'] + 1)
        session.wait(seconds_to_wait + 10, msg)

    html = session.get(city_url + city_id)
    city = getCity(html)
    return city


def expandBuilding(session, cityId, building, waitForResources):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    cityId : int
    building : dict
    waitForResources : bool
    """
    current_level = building['level']
    if building['isBusy']:
        current_level += 1
    levels_to_upgrade = building['upgradeTo'] - current_level
    position = building['position']

    session.wait(5, max_random=15, info='Waiting to avoid race conditions with sendResourcesNeeded')

    for lv in range(levels_to_upgrade):
        city = waitForConstruction(session, cityId)
        building = city['position'][position]

        if building['canUpgrade'] is False and waitForResources is True:
            while building['canUpgrade'] is False:
                session.wait(60, 'Waiting to have some more resources')
                seconds = getMinimumWaitingTime(session)
                html = session.get(city_url + cityId)
                city = getCity(html)
                building = city['position'][position]
                # if no ships are comming, exit no matter if the building can or can't upgrade
                if seconds == 0:
                    break
                session.wait(seconds + 5, 'Waiting the ships to arrive')

        if building['canUpgrade'] is False:
            msg = 'City:{}\n'.format(city['cityName'])
            msg += 'Building:{}\n'.format(building['name'])
            msg += 'The building could not be completed due to lack of resources.\n'
            msg += 'Missed {:d} levels'.format(levels_to_upgrade - lv)
            logging.info(msg)
            sendToBot(session, msg)
            return

        url = 'action=CityScreen&function=upgradeBuilding&actionRequest={}&cityId={}&position={:d}&level={}&activeTab=tabSendTransporter&backgroundView=city&currentCityId={}&templateView={}&ajax=1'.format(actionRequest, cityId, position, building['level'], cityId, building['building'])
        resp = session.post(url)
        html = session.get(city_url + cityId)
        city = getCity(html)
        building = city['position'][position]
        if building['isBusy'] is False:
            msg = '{}: The building {} was not extended'.format(city['cityName'], building['name'])
            sendToBot(session, msg)
            sendToBot(session, resp)
            return

        msg = '{}: The building {} is being extended to level {:d}.'.format(city['cityName'], building['name'],
                                                                            building['level']+1)
        logging.info(msg)

    msg = '{}: The building {} finished extending to level: {:d}.'.format(city['cityName'], building['name'],
                                                                          building['level']+1)
    logging.info(msg)


def getCostsReducers(city):
    """
    Parameters
    ----------
    city : dict

    Returns
    -------
    reducers_per_material_level : dict[int, int]
    """
    reducers_per_material = [0] * len(materials_names)
    assert len(reducers_per_material) == 5

    for building in city['position']:
        if building['name'] == 'empty':
            continue
        lv = building['level']
        if building['building'] == 'carpentering':
            reducers_per_material[0] = lv
        elif building['building'] == 'vineyard':
            reducers_per_material[1] = lv
        elif building['building'] == 'architect':
            reducers_per_material[2] = lv
        elif building['building'] == 'optician':
            reducers_per_material[3] = lv
        elif building['building'] == 'fireworker':
            reducers_per_material[4] = lv
    return reducers_per_material


def getResourcesNeeded(session, city, building, current_level, final_level):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    city : dict
    building : dict
    current_level : int
    final_level : int

    Returns
    -------
    costs_per_material : dict[int, int]
    """
    # get html with information about buildings
    building_detail_url = 'view=buildingDetail&buildingId=0&helpId=1&backgroundView=city&currentCityId={}&templateView=ikipedia&actionRequest={}&ajax=1'.format(city['id'], actionRequest)
    building_detail_response = session.post(building_detail_url)
    building_detail = json.loads(building_detail_response, strict=False)
    building_html = building_detail[1][1][1]

    # get html with information about buildings costs
    regex_building_detail = r'<div class="(?:selected)? button_building ' + re.escape(building['building']) + r'"\s*onmouseover="\$\(this\)\.addClass\(\'hover\'\);" onmouseout="\$\(this\)\.removeClass\(\'hover\'\);"\s*onclick="ajaxHandlerCall\(\'\?(.*?)\'\);'
    match = re.search(regex_building_detail, building_html)
    building_costs_url = match.group(1)
    building_costs_url += 'backgroundView=city&currentCityId={}&templateView=buildingDetail&actionRequest={}&ajax=1'.format(city['id'], actionRequest)
    building_costs_response = session.post(building_costs_url)
    building_costs = json.loads(building_costs_response, strict=False)
    html_costs = building_costs[1][1][1]

    # if the user has all the resource saving studies, we save that in the session data (one less request)
    sessionData = session.getSessionData()
    if 'reduccion_inv_max' in sessionData:
        costs_reduction = 14
    else:
        # get the studies
        url = 'view=noViewChange&researchType=economy&backgroundView=city&currentCityId={}&templateView=researchAdvisor&actionRequest={}&ajax=1'.format(city['id'], actionRequest)
        rta = session.post(url)
        rta = json.loads(rta, strict=False)
        studies = rta[2][1]['new_js_params']
        studies = json.loads(studies, strict=False)
        studies = studies['currResearchType']

        # look for resource saving studies
        costs_reduction = 0
        for study in studies:
            if studies[study]['liClass'] != 'explored':
                continue
            link = studies[study]['aHref']
            if '2020' in link:
                costs_reduction += 2
            elif '2060' in link:
                costs_reduction += 4
            elif '2100' in link:
                costs_reduction += 8

        # if the user has all the resource saving studies, save that in the session data
        if costs_reduction == 14:
            sessionData['reduccion_inv_max'] = True
            session.setSessionData(sessionData)

    # calculate cost reductions
    costs_reduction /= 100
    costs_reduction = 1 - costs_reduction

    # get buildings that reduce the cost of upgrades
    costs_reductions = getCostsReducers(city)

    # get the type of resources that this upgrade will cost (wood, marble, etc)
    resources_types = re.findall(r'<th class="costs"><img src="(.*?)\.png"/></th>', html_costs)[:-1]

    # get the actual cost of each upgrade
    matches = re.findall(r'<td class="level">\d+</td>(?:\s+<td class="costs">.*?</td>)+', html_costs)

    # calculate the cost of the entire upgrade, taking into account all the possible reductions
    final_costs = [0] * len(materials_names)
    levels_to_upgrade = 0
    for match in matches:
        lv = re.search(r'"level">(\d+)</td>', match).group(1)
        lv = int(lv)

        if lv <= current_level:
            continue
        if lv > final_level:
            break

        levels_to_upgrade += 1
        # get the costs for the current level
        costs = re.findall(r'<td class="costs">([\d,\.]*)</td>', match)

        for i in range(len(costs)):
            #get hash from CDN images to identify the resource type
            resource_type = checkhash("https:" + resources_types[i] + ".png")

            for j in range(len(materials_names_tec)):
                name = materials_names_tec[j]
                if resource_type == name:
                    resource_index = j
                    break

            # get the cost of the current resource type
            cost = costs[i]
            cost = cost.replace(',', '').replace('.', '')
            cost = 0 if cost == '' else int(cost)

            # calculate all the reductions
            real_cost = Decimal(cost)
            # investigation reduction
            original_cost = Decimal(real_cost) / Decimal(costs_reduction)
            # special building reduction
            real_cost -= Decimal(original_cost) * (Decimal(costs_reductions[resource_index]) / Decimal(100))

            final_costs[resource_index] += math.ceil(real_cost)

    if levels_to_upgrade < final_level - current_level:
        print('This building only allows you to expand {:d} more levels'.format(levels_to_upgrade))
        msg = 'Expand {:d} levels? [Y/n]:'.format(levels_to_upgrade)
        rta = read(msg=msg, values=['Y', 'y', 'N', 'n', ''])
        if rta.lower() == 'n':
            return [-1, -1, -1, -1, -1]

    return final_costs


def sendResourcesNeeded(session, destination_city_id, city_origins, missing_resources):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    destination_city_id : int
    city_origins : dict
    missing_resources : dict[int, int]
    """

    info = '\nTransport resources to upload building\n'

    try:
        routes = []
        html = session.get(city_url + destination_city_id)
        cityD = getCity(html)
        for i in range(len(materials_names)):
            missing = missing_resources[i]
            if missing <= 0:
                continue

            # send the resources from each origin city
            for cityOrigin in city_origins[i]:
                if missing == 0:
                    break

                available = cityOrigin['availableResources'][i]
                send = min(available, missing)
                missing -= send
                toSend = [0] * len(materials_names)
                toSend[i] = send
                route = (cityOrigin, cityD, cityD['islandId'], *toSend)
                routes.append(route)
        executeRoutes(session, routes)
    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
        # no s.logout() because this is a thread, not a process


def chooseResourceProviders(session, cities_ids, cities, city_id, resource, missing):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    cities_ids : list[int]
    cities : dict[int, dict]
    city_id : int
    resource : int
    missing : int
    """
    global sendResources
    sendResources = True
    global expand
    expand = True

    banner()
    print('From what cities obtain {}?'.format(materials_names[resource].lower()))

    tradegood_initials = [material_name[0] for material_name in materials_names]

    origin_cities = []
    total_available = 0
    for cityId in cities_ids:
        if cityId == city_id:
            continue

        html = session.get(city_url + cityId)
        city = getCity(html)

        available = city['availableResources'][resource]
        if available == 0:
            continue

        # ask the user it this city should provide resources
        tradegood_initial = tradegood_initials[int(cities[cityId]['tradegood'])]
        city_name_padded = "{: >{len}}".format(
            decodeUnicodeEscape(cities[cityId]['name']),
            len=MAXIMUM_CITY_NAME_LENGTH,
        )
        msg = '{} ({}): {} [Y/n]:'.format(city_name_padded, tradegood_initial, addThousandSeparator(available))
        choice = read(msg=msg, values=['Y', 'y', 'N', 'n', ''])
        if choice.lower() == 'n':
            continue

        # if so, save the city and calculate the total amount resources to send
        total_available += available
        origin_cities.append(city)
        # if we have enough resources, return
        if total_available >= missing:
            return origin_cities

    # if we reach this part, there are not enough resources to expand the building
    print('\nThere are not enough resources.')

    if len(origin_cities) > 0:
        print('\nSend the resources anyway? [Y/n]')
        choice = read(values=['y', 'Y', 'n', 'N', ''])
        if choice.lower() == 'n':
            sendResources = False

    print('\nTry to expand the building anyway? [y/N]')
    choice = read(values=['y', 'Y', 'n', 'N', ''])
    if choice.lower() == 'n' or choice == '':
        expand = False

    return origin_cities


def sendResourcesMenu(session, city_id, missing):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    city_id : int
    missing : list[int, int]
    """
    global thread
    cities_ids, cities = getIdsOfCities(session)
    origins = {}
    # for each missing resource, choose providers
    for resource in range(len(missing)):
        if missing[resource] <= 0:
            continue

        origin_cities = chooseResourceProviders(session, cities_ids, cities, city_id, resource, missing[resource])
        if sendResources is False and expand:
            print('\nThe building will be expanded if possible.')
            enter()
            return
        elif sendResources is False:
            return
        origins[resource] = origin_cities

    if expand:
        print('\nThe resources will be sent and the building will be expanded if possible.')
    else:
        print('\nThe resources will be sent.')

    enter()

    # create a new thread to send the resources
    thread = threading.Thread(target=sendResourcesNeeded, args=(session, city_id, origins, missing,))
    thread.start()


def getBuildingToExpand(session, cityId):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    cityId : int

    Returns
    -------
    building : dict
    """
    html = session.get(city_url + cityId)
    city = getCity(html)

    banner()
    # show the buildings available to expand (ignore empty spaces)
    print('Which building do you want to expand?\n')
    print('(0)\tExit')
    buildings = [building for building in city['position'] if building['name'] != 'empty']
    for i, building in enumerate(buildings):
        if building['isMaxLevel'] is True:
            color = bcolors.BLACK
        elif building['canUpgrade'] is True:
            color = bcolors.GREEN
        else:
            color = bcolors.RED

        upgrading = '+' if building['isBusy'] is True else ' '
        print("({})\tlvl {: >2}{}  {}{}{}".format(i+1, building['level'], upgrading, color, building['name'], bcolors.ENDC))

    selected_building_id = read(min=0, max=len(buildings))
    if selected_building_id == 0:
        return None

    building = buildings[selected_building_id - 1]

    current_level = int(building['level'])
    # if the building is being expanded, add 1 level
    if building['isBusy']:
        current_level += 1

    banner()
    print('building:{}'.format(building['name']))
    print('current level:{}'.format(current_level))

    final_level = read(min=current_level, msg='increase to level:')
    building['upgradeTo'] = final_level

    return building
def checkhash(url):
    m = hashlib.md5()
    r = requests.get(url)
    for data in r.iter_content(8192):
        m.update(data)
        if m.hexdigest() == config.material_img_hash[0]:
            material = 'wood'
        elif m.hexdigest() == config.material_img_hash[1]:
            material = 'wine'
        elif m.hexdigest() == config.material_img_hash[2]:
            material = 'marble'
        elif m.hexdigest() == config.material_img_hash[3]:
            material = 'glass'
        elif m.hexdigest() == config.material_img_hash[4]:
            material = 'sulfur'
        else:
            continue
    return material

def constructionList(session, event, stdin_fd, predetermined_input):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    try:
        global expand
        global sendResources
        expand = True
        sendResources = True

        banner()
        wait_resources = False
        print('In which city do you want to expand a building?')
        city = chooseCity(session)
        cityId = city['id']
        building = getBuildingToExpand(session, cityId)
        if building is None:
            event.set()
            return

        current_level = building['level']
        if building['isBusy']:
            current_level += 1
        final_level = building['upgradeTo']

        # calculate the resources that are needed
        resourcesNeeded = getResourcesNeeded(session, city, building, current_level, final_level)
        if -1 in resourcesNeeded:
            event.set()
            return

        print('\nMaterials needed:')
        for i, name in enumerate(materials_names):
            amount = resourcesNeeded[i]
            if amount == 0:
                continue
            print('- {}: {}'.format(name, addThousandSeparator(amount)))
        print('')

        # calculate the resources that are missing
        missing = [0] * len(materials_names)
        for i in range(len(materials_names)):
            if city['availableResources'][i] < resourcesNeeded[i]:
                missing[i] = resourcesNeeded[i] - city['availableResources'][i]

        # show missing resources to the user
        if sum(missing) > 0:
            print('\nMissing:')
            for i in range(len(materials_names)):
                if missing[i] == 0:
                    continue
                name = materials_names[i].lower()
                print('{} of {}'.format(addThousandSeparator(missing[i]), name))
            print('')

            # if the user wants, send the resources from the selected cities
            print('Automatically transport resources? [Y/n]')
            rta = read(values=['y', 'Y', 'n', 'N', ''])
            if rta.lower() == 'n':
                print('Proceed anyway? [Y/n]')
                rta = read(values=['y', 'Y', 'n', 'N', ''])
                if rta.lower() == 'n':
                    event.set()
                    return
            else:
                wait_resources = True
                sendResourcesMenu(session, cityId, missing)
        else:
            print('\nYou have enough materials')
            print('Proceed? [Y/n]')
            rta = read(values=['y', 'Y', 'n', 'N', ''])
            if rta.lower() == 'n':
                event.set()
                return
    except KeyboardInterrupt:
        event.set()
        return

    session.setProcessObjective(
        action='Upgrade Building',
        objective='{} to {}'.format(building['name'], final_level),
        target_city_name=city['cityName']
    )

    set_child_mode(session)
    event.set()

    info = '\nUpgrade building\n'
    info = info + 'City: {}\nBuilding: {}. From {:d}, to {:d}'.format(city['cityName'], building['name'], current_level, final_level)

    setInfoSignal(session, info)
    try:
        if expand:
            expandBuilding(session, cityId, building, wait_resources)
        elif thread:
            thread.join()
    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()
