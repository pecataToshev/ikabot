#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from ikabot.bot.bot import Bot
from ikabot.helpers.gui import daysHoursMinutes
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

            for military_movement in [mov for mov in military_movements if mov['isHostile']]:
                event_id = military_movement['event']['id']
                current_attacks.append(event_id)

                # if we already alerted this, do nothing
                if event_id not in known_attacks:
                    arrival_time = self.__notify_attack_coming(military_movement)
                    known_attacks[event_id] = arrival_time

            # remove old attacks from knownAttacks
            for event_id in known_attacks:
                if event_id not in current_attacks:
                    known_attacks.pop(event_id)

            self._wait(
                seconds=self.seconds_between_checks,
                info='{} attacks coming'.format(len(known_attacks)),
                max_random=10,
            )

    def __notify_attack_coming(self, military_movement):
        arrival_time = int(military_movement['eventTime'])

        # get information about the attack
        mission_text = military_movement['event']['missionText']
        origin = military_movement['origin']
        target = military_movement['target']
        amount_troops = military_movement['army']['amount']
        amount_fleets = military_movement['fleet']['amount']
        time_left = arrival_time - time.time()

        # send alert
        msg = '-- ALERT --\n'
        msg += mission_text + '\n'
        msg += 'from the city {} of {}\n'.format(origin['name'], origin['avatarName'])
        msg += 'a {}\n'.format(target['name'])
        msg += '{} units\n'.format(amount_troops)
        msg += '{} fleet\n'.format(amount_fleets)
        msg += 'arrival in: {}\n'.format(daysHoursMinutes(int(time_left)))
        self.telegram.send_message(msg)

        return arrival_time
