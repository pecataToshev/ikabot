import json
import math
import re
from decimal import Decimal

from ikabot.bot.transportGoodsBot import TransportGoodsBot
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.naval import get_military_and_see_movements


def get_current_attacks(ikariam_service, city_id, island_id):

    movements = get_military_and_see_movements(ikariam_service, city_id)
    curr_attacks = []

    for movement in movements:
        if movement['event']['mission'] != 13:
            continue
        if movement['target']['islandId'] != int(island_id):
            continue
        if movement['event']['isReturning'] != 0:
            continue
        if movement['origin']['cityId'] == -1:
            continue

        curr_attacks.append(movement)

    return curr_attacks


def filter_loading(attacks):
    return [attack for attack in attacks if attack['event']['missionState'] == 1]


def filter_traveling(attacks):
    return [attack for attack in attacks if attack['event']['missionState'] == 2 and attack['event']['canAbort']]


def filter_fighting(attacks):
    return [attack for attack in attacks if attack['event']['missionState'] == 2 and attack['event']['canRetreat']]


def get_units(session, city):
    params = {
        'view': 'cityMilitary',
        'activeTab': 'tabUnits',
        'cityId': city['id'],
        'backgroundView': 'city',
        'currentCityId': city['id'],
        'currentTab': 'multiTab1',
        'actionRequest': actionRequest,
        'ajax': '1'
    }

    resp = session.post(params=params)
    resp = json.loads(resp, strict=False)
    html = resp[1][1][1]
    html = html.split('<div class="fleet')[0]

    unit_id_names = re.findall(r'<div class="army (.*?)">\s*<div class="tooltip">(.*?)<\/div>', html)
    unit_amounts = re.findall(r'<td>(.*?)\s*</td>', html)

    units = {}
    for i in range(len(unit_id_names)):
        amount = int(unit_amounts[i].replace(',', '').replace('-', '0'))
        unit_id = unit_id_names[i][0][1:]
        unit_name = unit_id_names[i][1]
        units[unit_id] = {}
        units[unit_id]['name'] = unit_name
        units[unit_id]['amount'] = amount

    return units


def get_barbarians_lv(session, island):
    params = {"view": "barbarianVillage", "destinationIslandId": island['id'], "oldBackgroundView": "city", "cityWorldviewScale": "1", "islandId": island['id'], "backgroundView": "island", "currentIslandId": island['id'], "actionRequest": actionRequest, "ajax": "1"}
    resp = session.post(params=params)
    resp = json.loads(resp, strict=False)

    level = int(resp[2][1]['js_islandBarbarianLevel']['text'])
    gold = int(resp[2][1]['js_islandBarbarianResourcegold']['text'].replace(',', ''))

    resources = [0] * len(materials_names)
    for i in range(len(materials_names)):
        if i == 0:
            resources[i] = int(resp[2][1]['js_islandBarbarianResourceresource']['text'].replace(',', ''))
        else:
            resources[i] = int(resp[2][1]['js_islandBarbarianResourcetradegood{:d}'.format(i)]['text'].replace(',', ''))

    html = resp[1][1][1]
    troops = re.findall(r'<div class="army \w*?">\s*<div class=".*?">(.*?)</div>\s*</div>\s*</td>\s*</tr>\s*<tr>\s*<td class="center">\s*(\d+)', html)

    total_cargo = sum(resources)
    ships = math.ceil(Decimal(total_cargo) / Decimal(TransportGoodsBot.MAXIMUM_SHIP_SIZE))

    info = {
        'island_id': island['id'],
        'level': level,
        'gold': gold,
        'resources': resources,
        'troops': troops,
        'ships': ships
    }

    return info


def get_barbarians_info(ikariam_service, island_id):
    query = {
        'view': 'barbarianVillage',
        'destinationIslandId': island_id,
        'backgroundView': 'island',
        'currentIslandId': island_id,
        'actionRequest': actionRequest,
        'ajax': 1
    }
    resp = ikariam_service.post(params=query)
    resp = json.loads(resp, strict=False)
    return resp


def calc_travel_time(city, island, speed):
    if city['x'] == island['x'] and city['y'] == island['y']:
        return math.ceil(36000/speed)
    else:
        return math.ceil(1200 * math.sqrt(((city['x'] - island['x']) ** 2) + ((city['y'] - island['y']) ** 2)))


