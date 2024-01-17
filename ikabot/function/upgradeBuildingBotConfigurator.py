#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import math
import re
from decimal import Decimal

import requests

from ikabot import config
from ikabot.bot.transportGoodsBot import TransportGoodsBot, TransportJob
from ikabot.bot.upgradeBuildingBot import UpgradeBuildingBot
from ikabot.config import actionRequest, city_url, materials_names, materials_names_tec, \
    MAXIMUM_CITY_NAME_LENGTH
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator, banner, bcolors, decodeUnicodeEscape, enter
from ikabot.helpers.ikabotProcessListManager import IkabotProcessListManager
from ikabot.helpers.citiesAndIslands import chooseCity, getIdsOfCities
from ikabot.helpers.userInput import askUserYesNo, read


def getCostsReducers(city):
    """
    Parameters
    ----------
    city : dict

    Returns
    -------
    reducers_per_material_level : Dict[int, int]
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
    session : ikabot.web.ikariamService.IkariamService
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
    if session.db.get_stored_value('maxReductionCost'):
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
            session.db.store_value('maxReductionCost', True)

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


def chooseResourceProviders(cities, beneficent_city, resource, missing, send_resources, expand_anyway):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    cities : list[dict[]]
    beneficent_city : dict
    resource : int
    missing : int
    send_resources : bool/None
    expand_anyway : bool/None

    :returns bool, bool, bool, List[TransportJob]:
        if resources are enough
        should send the resources anyway
        should try to expand anyway
        transport routes to perform

    """
    banner()
    print('From what cities obtain {} ({} remaining)?'.format(materials_names[resource],
                                                              addThousandSeparator(missing)))

    tradegood_initials = [material_name[0] for material_name in materials_names]

    routes = []
    total_available = 0
    for city in cities:
        if city['id'] == beneficent_city['id']:
            continue

        available = city['availableResources'][resource]
        if available == 0:
            continue

        # ask the user it this city should provide resources
        tradegood_initial = tradegood_initials[int(city['tradegood'])]
        city_name_padded = "{: >{len}}".format(
            decodeUnicodeEscape(city['name']),
            len=MAXIMUM_CITY_NAME_LENGTH,
        )

        _msg = '{} ({}): {}'.format(city_name_padded, tradegood_initial, addThousandSeparator(available))
        if not askUserYesNo(_msg):
            continue

        # if so, save the city and calculate the total amount resources to send
        total_available += available
        to_send = [0] * len(materials_names)
        to_send[resource] = available
        routes.append(TransportJob(city, beneficent_city, to_send))
        # if we have enough resources, return
        if total_available >= missing:
            return True, send_resources, expand_anyway, routes

    # if we reach this part, there are not enough resources to expand the building
    print('\nThere are not enough resources.')

    if len(routes) > 0 and send_resources is None:
        send_resources = askUserYesNo('Send the resources anyway')

    if expand_anyway is None:
        expand_anyway = askUserYesNo('Try to expand the building anyway')

    return False, send_resources, expand_anyway, routes


def sendResourcesMenu(ikariam_service, beneficent_city_id, missing):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    beneficent_city_id : int
    missing : list[int, int]
    """
    cities_ids, _ = getIdsOfCities(ikariam_service)
    cities = [getCity(ikariam_service.get(city_url + str(city_id))) for city_id in cities_ids]
    beneficent_city = [c for c in cities if c['id'] == beneficent_city_id][0]
    send_resources = None
    expand_anyway = None

    enough_resources = True
    all_routes = []
    # for each missing resource, choose providers
    for resource in range(len(missing)):
        if missing[resource] <= 0:
            continue

        enough_resource, send_resources, expand_anyway, routes = chooseResourceProviders(
            cities=cities,
            beneficent_city=beneficent_city,
            resource=resource,
            missing=missing[resource],
            send_resources=send_resources,
            expand_anyway=expand_anyway
        )
        enough_resources = enough_resources and enough_resource
        if send_resources is False and expand_anyway:
            print('\nThe building will be expanded if possible.')
            enter()
            return None
        elif send_resources is False or expand_anyway is False:
            return None
        all_routes.append(routes)

    if enough_resources:
        print('The resources will be sent.')
    else:
        print('The resources will be sent and the building will be expanded if possible.')

    process = TransportGoodsBot(ikariam_service, {'jobs': all_routes}).start(
        action='Transport Goods',
        objective='Provide upgrade building resources',
        target_city=beneficent_city['name']
    )

    enter()
    return process


def getBuildingToExpand(city):
    """
    Parameters
    ----------
    cityId : dict

    Returns
    -------
    building : dict
    """
    # show the buildings available to expand (ignore empty spaces)
    print('Which building do you want to expand?\n')
    print('(0)\tExit')
    buildings = [building for building in city['position'] if building['name'] != 'empty']
    buildings = [buildings[0]] + sorted(buildings[1:], key=lambda b: b['name'])
    for i, building in enumerate(buildings):
        if building['isMaxLevel'] is True:
            color = bcolors.BLACK
        elif building['canUpgrade'] is True:
            color = bcolors.GREEN
        else:
            color = bcolors.RED

        upgrading = '+' if building['isBusy'] is True else ' '
        position_prefix = ' ' if building['position'] < 10 else ''
        print("{}{:>2}) lvl {: >2}{}  {}{}{}".format(
            color,
            i+1,
            building['level'],
            upgrading,
            position_prefix,
            building['positionAndName'],
            bcolors.ENDC)
        )

    selected_building_id = read(min=0, max=len(buildings))
    if selected_building_id == 0:
        return None

    building = buildings[selected_building_id - 1]

    current_level = int(building['level'])
    # if the building is being expanded, add 1 level
    if building['isBusy']:
        current_level += 1

    print()
    print()
    print('         building:', building['positionAndName'])
    print('    current level:', current_level)
    building['targetLevel'] = read(min=current_level+1, msg='increase to level: ')

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


def __print_related_processes(db, city_name):
    process_manager = IkabotProcessListManager(db)
    related_processes = process_manager.get_process_list(filters=[['targetCity', '==', city_name]])
    if len(related_processes) <= 0:
        return

    process_manager.print_proces_table(
        process_list=related_processes
    )


def upgrade_building_bot_configurator(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """

    banner()
    print('In which city do you want to expand a building?')
    city = chooseCity(ikariam_service)
    city_id = city['id']

    banner()
    print(city['cityName'])
    __print_related_processes(db, city['cityName'])

    building = getBuildingToExpand(city)
    if building is None:
        return

    target_level = building['upgradeTo']
    current_level = UpgradeBuildingBot.get_building_level(building)

    # calculate the resources that are needed
    resources_needed = getResourcesNeeded(ikariam_service, city, building, current_level, target_level)
    if -1 in resources_needed:
        return

    print('\nMaterials needed:')
    for i, name in enumerate(materials_names):
        amount = resources_needed[i]
        if amount == 0:
            continue
        print('- {}: {}'.format(name, addThousandSeparator(amount)))
    print('')

    # calculate the resources that are missing
    missing = [0] * len(materials_names)
    for i in range(len(materials_names)):
        if city['availableResources'][i] < resources_needed[i]:
            missing[i] = resources_needed[i] - city['availableResources'][i]

    # show missing resources to the user
    _transport_process = None
    if sum(missing) > 0:
        print('\nMissing:')
        for i in range(len(materials_names)):
            if missing[i] == 0:
                continue
            name = materials_names[i].lower()
            print('{} of {}'.format(addThousandSeparator(missing[i]), name))
        print('')

        # if the user wants, send the resources from the selected cities
        if not askUserYesNo('Automatically transport resources'):
            if not askUserYesNo('Proceed anyway'):
                return
        else:
            _transport_process = sendResourcesMenu(ikariam_service, city_id, missing)
    else:
        print('\nYou have enough materials')
        if not askUserYesNo('Proceed'):
            return

    UpgradeBuildingBot(
        ikariam_service=ikariam_service,
        bot_config={
            'cityId': city['id'],
            'cityName': city['name'],
            'building': building['positionAndName'],
            'transport_resources_pid': None if _transport_process is None else _transport_process.pid
        }
    ).start(
        action='Upgrade Building',
        objective='{} to {}'.format(building['positionAndName'], target_level),
        target_city=city['cityName']
    )
