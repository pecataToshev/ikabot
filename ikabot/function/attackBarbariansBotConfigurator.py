#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from ikabot.bot.attackBarbariansBot import AttackBarbariansBot
from ikabot.config import island_url, materials_names
from ikabot.helpers.barbarians import get_barbarians_lv, get_units
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getIsland
from ikabot.helpers.gui import addThousandSeparator, banner, enter
from ikabot.helpers.naval import getTotalShips
from ikabot.helpers.citiesAndIslands import chooseCity, getIslandsIds
from ikabot.helpers.userInput import read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def choose_island(session):
    idsIslands = getIslandsIds(session)
    islands = []
    for idIsland in idsIslands:
        html = session.get(island_url + idIsland)
        island = getIsland(html)
        islands.append(island)

    if len(islands) == 1:
        return islands[0]

    islands.sort(key=lambda island: island['id'])

    longest_island_name_length = 0
    for island in islands:
        longest_island_name_length = max(len(island['name']), longest_island_name_length)

    def pad(island_name):
        return ' ' * (longest_island_name_length - len(island_name)) + island_name

    print('In which island do you want to attack the barbarians?')
    print(' 0) Exit')
    for i, island in enumerate(islands):
        num = ' ' + str(i+1) if i < 9 else str(i+1)
        if island['barbarians']['destroyed'] == 1:
            warn = '(currently destroyed)'
        else:
            warn = ''
        print('{}) [{}:{}] {} ({}) : barbarians lv: {} ({}) {}'.format(num, island['x'], island['y'], pad(island['name']), materials_names[int(island['tradegood'])][0].upper(), island['barbarians']['level'], island['barbarians']['city'], warn))

    index = read(min=0, max=len(islands))
    if index == 0:
        return None
    else:
        return islands[index-1]

def plan_attack(session, city, babarians_info):
    total_units = get_units(session, city)

    if sum([total_units[unit_id]['amount'] for unit_id in total_units]) == 0:
        print('You don\'t have any troops in this city!')
        enter()
        return None

    plan = []
    total_ships = None
    last = False
    while True:

        banner()

        units_available = {}
        for unit_id in total_units:

            already_sent = sum([p['units'][u] for p in plan for u in p['units'] if u == unit_id])
            if already_sent < total_units[unit_id]['amount']:
                units_available[unit_id] = {}
                units_available[unit_id]['amount'] = total_units[unit_id]['amount'] - already_sent
                units_available[unit_id]['name'] = total_units[unit_id]['name']

        if len(units_available) == 0:
            print('No more troops available to send')
            enter()
            break

        attack_round = {}
        attack_round['units'] = {}
        print('Which troops do you want to send?')
        for unit_id in units_available:
            unit_amount = units_available[unit_id]['amount']
            unit_name = units_available[unit_id]['name']
            amount_to_send = read(msg='{} (max: {}): '.format(unit_name, addThousandSeparator(unit_amount)), max=unit_amount, default=0)
            if amount_to_send > 0:
                attack_round['units'][unit_id] = amount_to_send
        print('')

        attack_round['loot'] = last
        if last:
            attack_round['round'] = len(plan) + 1
        else:
            if len(plan) > 0:
                round_def = len(plan) + 1
                attack_round['round'] = read(msg='In which battle round do you want to send them? (min: 2, default: {:d}): '.format(round_def), min=2, default=round_def)
            else:
                attack_round['round'] = 1
        print('')

        if last is False:
            if total_ships is None:
                total_ships = getTotalShips(session)
            max_ships = total_ships - sum([ar['ships'] for ar in plan])
            if max_ships > 0:
                attack_round['ships'] = read(msg='How many ships do you want to send in this round? (min: 0, max: {:d}): '.format(max_ships), min=0, max=max_ships)
                print('')
            else:
                attack_round['ships'] = 0

        plan.append(attack_round)

        if last:
            break

        print('Do you want to send another round of troops? [y/N]')
        resp = read(values=['y', 'Y', 'n', 'N'], default='n')
        if resp.lower() != 'y':
            print('')
            print('Do you want to select the troops that will be used to collect the remaining resources? (they need to destroy the wall) [y/N]')
            resp = read(values=['y', 'Y', 'n', 'N'], default='n')
            if resp.lower() != 'y':
                break
            else:
                last = True

    plan.sort(key=lambda ar: ar['round'])
    return plan


def attack_barbarians_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    island = choose_island(ikariam_service)
    if island is None:
        return

    babarians_info = get_barbarians_lv(ikariam_service, island)

    banner()
    print('The barbarians have:')
    for name, amount in babarians_info['troops']:
        print('{} units of {}'.format(amount, name))
    print('')

    print('From which city do you want to attack?')
    city = chooseCity(ikariam_service)

    plan = plan_attack(ikariam_service, city, babarians_info)
    if plan is None:
        return

    banner()
    print('The barbarians in [{}:{}] will be attacked.'.format(island['x'], island['y']))


    AttackBarbariansBot(
        ikariam_service=ikariam_service,
        bot_config={
            'island': island,
            'city': city,
            'plan': plan,
            'babariansInfo': babarians_info,
        }
    ).start(
        action='Attack Barbarians',
        objective='Barbarians level {}'.format(babarians_info['level']),
        target_city=city['name'],
    )

    enter()
