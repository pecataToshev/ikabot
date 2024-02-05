#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime

from ikabot.bot.bot import Bot
from ikabot.helpers.gui import bcolors, daysHoursMinutes
from ikabot.helpers.naval import get_military_and_see_movements


class AttacksMonitoringBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.seconds_between_checks = bot_config['waitMinutes'] * 60

    def _get_process_info(self) -> str:
        return '\nI check for attacks every {:d} minutes\n'.format(self.bot_config['waitMinutes'])

    def _start(self) -> None:
        known_attacks = {}
        while True:
            current_attacks = []
            # get the militaryMovements
            military_movements = get_military_and_see_movements(self.ikariam_service)

            for military_movement in military_movements:
                if not military_movement['isHostile']:
                    continue

                event_id = military_movement['event']['id']
                current_attacks.append(event_id)

                # if we already alerted this, do nothing
                if event_id not in known_attacks:
                    self.__notify_attack_coming(military_movement)
                    known_attacks[event_id] = military_movement

            # remove old attacks from knownAttacks
            for event_id in dict(known_attacks):  # prevents RuntimeError: dictionary changed size during iteration
                if event_id not in current_attacks:
                    known_attacks.pop(event_id)

            __attacks = bcolors.GREEN + 'No'
            __suffix = ''
            if len(known_attacks) > 0:
                __data = {}
                for a in known_attacks.values():
                    __t = __data.get(a['event']['type'], [])
                    __t.append(a['target']['name'])
                    __data.update({a['event']['type']: __t})
                __attacks = bcolors.RED + str(len(known_attacks))
                __suffix = ': ' + str(__data)

            self._wait(
                seconds=self.seconds_between_checks,
                info='{} attacks coming{}{}'.format(__attacks, __suffix, bcolors.ENDC),
                max_random=10,
            )

    def __notify_attack_coming(self, attack):
        logging.debug('Found attack: {}'.format(attack))
        arrival_time = int(attack['eventTime'])

        # get information about the attack
        __type = attack['event']['type']
        origin = attack['origin']
        target = attack['target']

        # send alert
        msg = '-- ATTACK ALERT --\n'
        msg += '{}: {}\n'.format(__type, attack['event']['missionText'])
        msg += '{} ({}) -> {}\n'.format(origin['name'], origin['avatarName'], target['name'])
        if __type != 'piracy':
            msg += '{} units; {} fleet\n'.format(attack['army']['amount'], attack['fleet']['amount'])

        msg += 'Arrival: {} (in {})'.format(
            datetime.fromtimestamp(arrival_time).strftime('%Y-%m-%d %H:%M:%S'),
            daysHoursMinutes(int(arrival_time - time.time()))
        )

        self.telegram.send_message(msg)
