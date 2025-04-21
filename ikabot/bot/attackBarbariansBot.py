#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import time
from decimal import Decimal

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, island_url
from ikabot.helpers.barbarians import (calc_travel_time, filter_fighting,
                                       filter_loading, filter_traveling,
                                       get_barbarians_info, get_barbarians_lv,
                                       get_current_attacks, get_units)
from ikabot.helpers.getJson import getIsland
from ikabot.helpers.naval import TransportShip, get_transport_ships_size
from ikabot.helpers.planRoutes import waitForAvailableShips


class AttackBarbariansBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.island = bot_config['island']
        self.city = bot_config['city']
        self.plan = bot_config['plan']
        self.babarians_info = bot_config['babariansInfo']

    def _get_process_info(self) -> str:
        return 'I attack the barbarians in [{}:{}]'.format(self.island['x'], self.island['y'])
    
    def __get_island(self):
        return getIsland(self.ikariam_service.get(island_url + self.island['id']))

    def _start(self) -> None:
        units_data = {}
        battle_start = None
    
        for attack_round in self.plan:
    
            # this round is supposed to get the resources
            if attack_round['loot']:
                break
    
            attack_data = {'action': 'transportOperations', 'function': 'attackBarbarianVillage', 'actionRequest': actionRequest, 'islandId': island['id'], 'destinationCityId': 0, 'cargo_army_304_upkeep': 3, 'cargo_army_304': 0, 'cargo_army_315_upkeep': 1, 'cargo_army_315': 0, 'cargo_army_302_upkeep': 4, 'cargo_army_302': 0, 'cargo_army_303_upkeep': 3, 'cargo_army_303': 0, 'cargo_army_312_upkeep': 15, 'cargo_army_312': 0, 'cargo_army_309_upkeep': 45, 'cargo_army_309': 0, 'cargo_army_307_upkeep': 15, 'cargo_army_307': 0, 'cargo_army_306_upkeep': 25, 'cargo_army_306': 0, 'cargo_army_305_upkeep': 30, 'cargo_army_305': 0, 'cargo_army_311_upkeep': 20, 'cargo_army_311': 0, 'cargo_army_310_upkeep': 10, 'cargo_army_310': 0, 'transporter': 0, 'barbarianVillage': 1, 'backgroundView': 'island', 'currentIslandId': island['id'], 'templateView': 'plunder', 'ajax': 1}
    
            attack_data, ships_needed, travel_time = self.__load_troops(attack_round, units_data, attack_data)
    
            try:
                self.__wait_for_round(travel_time, battle_start, attack_round['round'])
            except AssertionError:
                # battle ended before expected
                break
    
            ships_available = 0
            while ships_available < ships_needed:
                ships_available = waitForAvailableShips(self.ikariam_service, self._wait)
            ships_available -= ships_needed
    
            # if the number of available troops changed, the POST request might not work as intended
    
            attack_data['transporter'] = min(self.babarians_info['ships'], attack_round['ships'], ships_available)
    
            # send new round
            self.ikariam_service.post(params=attack_data)
    
            if attack_round['round'] == 1:
                battle_start = time.time() + travel_time
    
        self.__wait_until_attack_is_over()
    
        last_round = self.plan[-1]
        if last_round['loot']:
            self.__loot(units_data, last_round)
            
    def __loot(self, units_data, loot_round):
        while True:
    
            attack_data = {
                'action': 'transportOperations',
                'function': 'attackBarbarianVillage',
                'actionRequest': actionRequest,
                'islandId': self.island['id'],
                'destinationCityId': 0,
                'cargo_army_304_upkeep': 3,
                'cargo_army_304': 0,
                'cargo_army_315_upkeep': 1,
                'cargo_army_315': 0,
                'cargo_army_302_upkeep': 4,
                'cargo_army_302': 0,
                'cargo_army_303_upkeep': 3,
                'cargo_army_303': 0,
                'cargo_army_312_upkeep': 15,
                'cargo_army_312': 0,
                'cargo_army_309_upkeep': 45,
                'cargo_army_309': 0,
                'cargo_army_307_upkeep': 15,
                'cargo_army_307': 0,
                'cargo_army_306_upkeep': 25,
                'cargo_army_306': 0,
                'cargo_army_305_upkeep': 30,
                'cargo_army_305': 0,
                'cargo_army_311_upkeep': 20,
                'cargo_army_311': 0,
                'cargo_army_310_upkeep': 10,
                'cargo_army_310': 0,
                'transporter': 0,
                'barbarianVillage': 1,
                'backgroundView': 'island',
                'currentIslandId': self.island['id'],
                'templateView': 'plunder',
                'ajax': 1
            }
    
            # make sure we have ships on the port
            ships_available = waitForAvailableShips(self.ikariam_service, self._wait)
    
            # if the barbarians are active again or all the resources were stolen, return
            island = self.__get_island()
            destroyed = island['barbarians']['destroyed'] == 1
            resources = get_barbarians_lv(self.ikariam_service, island)['resources']
            if destroyed is False or sum(resources) == 0:
                return
    
            # if we already sent an attack and we still have ships on the port, it was the last one
            attacks = get_current_attacks(self.ikariam_service, self.city['id'], island['id'])
            attacks = filter_loading(attacks) + filter_traveling(attacks)
            if len(attacks) > 0:
                return
    
            attack_data, ships_needed, travel_time = self.__load_troops(loot_round, units_data, attack_data, sum(resources))
            attack_data['transporter'] = min(ships_available, ships_needed)
    
            # make sure we have time to send the attack
            time_left = None
            resp = get_barbarians_info(self.ikariam_service, island['id'])
            if 'barbarianCityCooldownTimer' in resp[2][1]:
                time_left = resp[2][1]['barbarianCityCooldownTimer']['countdown']['enddate']
                time_left -= time.time()
            if time_left is not None and travel_time > time_left:
                return
    
            # send attack
            self.ikariam_service.post(params=attack_data)


    def __load_troops(self, attack_round, units_data, attack_data, extra_cargo=0):
        ship_size = get_transport_ships_size(self.ikariam_service, self.city['id'], TransportShip.TRANSPORT_SHIP)
        ships_needed = Decimal(extra_cargo) / Decimal(ship_size)
        speeds = []
        current_units = get_units(self.ikariam_service, self.city)
        for unit_id in attack_round['units']:
            amount_to_send = min(attack_round['units'][unit_id], current_units[unit_id]['amount'])
            attack_data['cargo_army_{}'.format(unit_id)] = amount_to_send
    
            if unit_id not in units_data:
                units_data[unit_id] = get_unit_data(self.ikariam_service, self.city['id'], unit_id)
    
            speeds.append(units_data[unit_id]['speed'])
    
            if city_is_in_island(self.city, island) is False:
                weight = units_data[unit_id]['weight']
                ships_needed += Decimal(amount_to_send * weight) / Decimal(ship_size)
    
        ships_needed = math.ceil(ships_needed)
        speed = min(speeds)
        travel_time = calc_travel_time(self.city, island, speed)
        return attack_data, ships_needed, travel_time


    def __wait_for_round(self, travel_time, battle_start, round_number):
        if round_number == 1:
            self.__wait_until_can_attack(travel_time)
        else:
            wait_time = battle_start + (round_number - 2) * 15 * 60
            wait_time -= time.time()
            wait_time -= travel_time
            self._wait(wait_time + 5, 'Waiting for round ' + round_number)
    
            if battle_start < time.time():
                island = self.__get_island()
                assert island['barbarians']['underAttack'] == 1, "the battle ended before expected"
    
    
    def __wait_until_can_attack(self, travel_time=0):
        island = self.__get_island()
    
        if island['barbarians']['underAttack'] == 0 and island['barbarians']['destroyed'] == 0:
            # an attack might be on its way
            self._set_process_info('An attack is on its way')
            self.__wait_for_arrival()
            island = self.__get_island()
    
        if island['barbarians']['underAttack'] == 1:
            # a battle is taking place
            attacks = get_current_attacks(self.ikariam_service, self.city['id'], self.island['id'])
            attacks_fighting = filter_fighting(attacks)
            eventTimes = [attack['eventTime'] for attack in attacks_fighting]
            if len(eventTimes) > 0:
                wait_time = max(eventTimes)
                wait_time -= time.time()
                self._wait(wait_time + 5, 'A battle is taking place')
            self.__wait_until_can_attack(travel_time)
    
        if island['barbarians']['destroyed'] == 1:
            # the barbarians are destroyed and can't be attacked
            resp = get_barbarians_info(self.ikariam_service, island['id'])
            if 'barbarianCityCooldownTimer' in resp[2][1]:
                wait_time = resp[2][1]['barbarianCityCooldownTimer']['countdown']['enddate']
                wait_time -= time.time()
                wait_time -= travel_time
                self._wait(wait_time + 5, "The barbarians are destroyed and can't be attacked")
            self.__wait_until_can_attack(travel_time)


    def __wait_for_arrival(self):
        attacks = get_current_attacks(self.ikariam_service, self.city['id'], self.island['id'])
        attacks = filter_loading(attacks) + filter_traveling(attacks)
        eventTimes = [attack['eventTime'] for attack in attacks]

        if len(eventTimes) == 0:
            return

        wait_time = max(eventTimes)
        wait_time -= time.time()
        self._wait(wait_time + 5, 'Waiting for arrival')

        self.__wait_for_arrival()

    def wait_until_attack_is_over(self):
        island = self.__get_island()
    
        while island['barbarians']['destroyed'] == 0:
    
            attacks = get_current_attacks(self.ikariam_service, self.city['id'], island['id'])
            # the attack probably failed
            if len(attacks) == 0:
                return
    
            eventTimes = [attack['eventTime'] for attack in attacks]
            wait_time = min(eventTimes)
            wait_time -= time.time()
            self._wait(wait_time + 5, 'Waiting until attack is over')
    
            island = self.__get_island()

