#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import Colours
from ikabot.helpers.resources import getProductionPerSecond


class DonationBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.cities_ids = bot_config['cities_ids']
        self.cities_dict = bot_config['cities_dict']
        self.waiting_time = bot_config['waiting_time']
        self.max_random_waiting_time = bot_config['max_random_waiting_time']
        self.donate_method = bot_config['donate_method']

    def _get_process_info(self) -> str:
        pass

    def _start(self) -> None:
        for cityId in self.cities_ids:
            html = self.ikariam_service.get(city_url + cityId)
            city = getCity(html)
            self.cities_dict[cityId]['island'] = city['islandId']

        while True:
            for cityId in self.cities_ids:
                donation_type = self.cities_dict[cityId]['donation_type']
                if donation_type is None:
                    continue

                # get the storageCapacity and the wood this city has
                html = self.ikariam_service.get(city_url + cityId)
                city = getCity(html)

                self._set_process_info('Preparing donations', city['name'])

                wood = city['availableResources'][0]
                storageCapacity = city['storageCapacity']

                # get the percentage
                if self.donate_method == 1:
                    percentage = self.cities_dict[cityId]['percentage']
                    percentage /= 100

                    # calculate what is the amount of wood that should be preserved
                    max_wood = storageCapacity * percentage
                    max_wood = int(max_wood)

                    # calculate the wood that is exceeding the percentage
                    to_donate = wood - max_wood
                    if to_donate <= 0:
                        continue

                elif self.donate_method == 2:
                    # get current production rate if changed since starting the bot
                    (wood_prod, good_prod, typeGood) = getProductionPerSecond(self.ikariam_service, cityId)
                    percentage = self.cities_dict[cityId]['percentage']

                    # calculate the amount of wood to be donated from production, based on the given donation frequency
                    to_donate = int((wood_prod * percentage / 100) * (self.waiting_time * 60))
                    # Note: Connection delay can/will cause "inaccurate" donations especially with low waiting_time
                    if to_donate <= 0:
                        continue

                elif self.donate_method == 3:
                    percentage = self.cities_dict[cityId]['percentage']
                    # make sure the donation amount is never lower than resources available
                    max_wood = wood - percentage
                    max_wood = int(max_wood)

                    to_donate = percentage
                    if max_wood <= 0:
                        continue

                island_id = self.cities_dict[cityId]['island']
                self._set_process_info('Found {}{} Wood{} for donations. Donation type {}'.format(
                    Colours.MATERIALS[0],
                    to_donate,
                    Colours.Text.RESET,
                    donation_type
                ))

                # donate
                if donation_type == 'both':
                    forrest = int(to_donate / 2)
                    trade = int(to_donate / 2)
                    self.ikariam_service.post(
                        params={'islandId': island_id, 'type': 'resource', 'action': 'IslandScreen',
                                'function': 'donate',
                                'donation': forrest, 'backgroundView': 'island', 'templateView': donation_type,
                                'actionRequest': actionRequest, 'ajax': '1'})
                    logging.info("I donated %d wood to the forest on island %s", forrest, island_id)
                    self._wait(1, max_random=5, info='Simulating user interaction')
                    self.ikariam_service.post(
                        params={'islandId': island_id, 'type': 'tradegood', 'action': 'IslandScreen',
                                'function': 'donate',
                                'donation': trade, 'backgroundView': 'island', 'templateView': donation_type,
                                'actionRequest': actionRequest, 'ajax': '1'})
                    logging.info("I donated %d wood to the tradegood on island %s", trade, island_id)
                else:
                    self.ikariam_service.post(
                        params={'islandId': island_id, 'type': donation_type, 'action': 'IslandScreen',
                                'function': 'donate', 'donation': to_donate, 'backgroundView': 'island',
                                'templateView': donation_type, 'actionRequest': actionRequest,
                                'ajax': '1'})
                    logging.info("I donated %d wood to the %s on island %s", to_donate, donation_type, island_id)

            self._wait(
                self.waiting_time * 60,
                info='Collecting wood for the next donation',
                max_random=self.max_random_waiting_time * 60,
            )
