#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url, materials_names
from ikabot.helpers.buildings import extract_target_building, get_building_info
from ikabot.helpers.getJson import getCity


class TrainArmyBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.build_function = 'buildUnits' if bot_config['trainTroops'] else 'buildShips',
        self.units_type = 'troops' if bot_config['trainTroops'] else 'fleet'
        self.building_building = 'barracks' if bot_config['trainTroops'] else 'shipyard'
        self.city_id = bot_config['cityId']
        self.trainings = bot_config['trainings']

    def _get_process_info(self) -> str:
        return "I train {} in {}".format(self.units_type, self.bot_config['cityName'])

    def _start(self) -> None:
        # total number of units to create
        if sum([unit['cantidad'] for training in self.trainings for unit in training]) == 0:
            return

        training_index = 0
        while training_index < len(self.trainings):
            training = self.trainings[training_index]
            city = getCity(self.ikariam_service.get(city_url + self.city_id))
            building = extract_target_building(city, self.building_building)

            if building is None:
                self.telegram.send_message("Building {} disappeared in {}. Aborting training job!".format(
                    self.building_building, city['name']
                ))
                return

            if self.__wait_for_training(building, training_index):
                # refresh data after sleeping (waiting)
                continue

            resources_available = city['availableResources'].copy()
            resources_available.append(city['freeCitizens'])

            # for each unit type in training
            for unit in training:

                # calculate how many units can actually be trained based on the resources available
                unit['train'] = unit['cantidad']

                for i in range(len(materials_names)):
                    material_name = materials_names[i].lower()
                    if material_name in unit['costs']:
                        limiting = resources_available[i] // unit['costs'][material_name]
                        unit['train'] = min(unit['train'], limiting)

                if 'citizens' in unit['costs']:
                    limiting = resources_available[len(materials_names)] // unit['costs']['citizens']
                    unit['train'] = min(unit['train'], limiting)

                # calculate the resources that will be left
                for i in range(len(materials_names)):
                    material_name = materials_names[i].lower()
                    if material_name in unit['costs']:
                        resources_available[i] -= unit['costs'][material_name] * unit['train']

                if 'citizens' in unit['costs']:
                    resources_available[len(materials_names)] -= unit['costs']['citizens'] * unit['train']

                unit['cantidad'] -= unit['train']

            # amount of units that will be trained
            total = sum([unit['train'] for unit in training])
            if total == 0:
                self.telegram.send_message('It was not possible to finish the training due to lack of resources.')
                return

            self.__train(training, building)
            training_index += 1

    def __train(self, trainings, building):
        """
        Parameters
        ----------
        trainings : list[dict]
        """
        payload = {
            'action': 'CityScreen',
            'function': self.build_function,
            'templateView': building['building'],
            'actionRequest': actionRequest,
            'cityId': self.city_id,
            'position': building['position'],
            'backgroundView': 'city',
            'currentCityId': self.city_id,
            'ajax': '1'
        }
        for training in trainings:
            payload[training['unit_type_id']] = training['train']
        self.ikariam_service.post(params=payload)

    def __wait_for_training(self, building, training_index):
        data = get_building_info(self.ikariam_service, self.city_id, building)
        html = data[1][1][1]
        seconds = re.search(r'\'buildProgress\', (\d+),', html)
        if seconds:
            seconds = seconds.group(1)
            seconds = int(seconds) - data[0][1]['time']
            self._wait(
                seconds=seconds + 5,
                info='Training in progress. {} remaining'.format(len(self.trainings) - training_index),
                max_random=10
            )
            return True
        return False
