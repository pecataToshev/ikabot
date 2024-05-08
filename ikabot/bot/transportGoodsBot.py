#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import sys
from decimal import Decimal
from typing import List, Union

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url, materials_names, SECONDS_IN_HOUR
from ikabot.helpers.citiesAndIslands import getCurrentCityId
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator
from ikabot.helpers.planRoutes import waitForAvailableShips


class TransportJob:
    def __init__(self, origin_city, target_city, resources):
        self.origin_city = origin_city
        self.target_city = target_city
        self.resources = resources

    def __repr__(self):
        return (f"{{'origin_city': {self.origin_city['name']}, "
                f"'target_city': {self.target_city['name']}, "
                f"'resources': {self.resources}}}")

    def __eq__(self, other):
        if not isinstance(other, TransportJob):
            return False
        return (
                self.origin_city == other.origin_city
                and self.target_city == other.target_city
                and self.resources == other.resources
        )


class TransportGoodsBot(Bot):
    """
    Performs transportations
    """
    MAXIMUM_SHIP_SIZE = 500
    DEFAULT_BATCH_SIZE = 20 * MAXIMUM_SHIP_SIZE

    def _get_process_info(self) -> str:
        return 'I execute transportation of resources'

    def _start(self) -> None:
        batch_size = self.bot_config.get('batchSize', None)
        jobs = self.optimize_jobs(self.bot_config['jobs'])

        """
        Execute jobs with max batch size.
        We ensure that we're not exceeding the maximum batch size from city by optimizing the jobs. By doing this 
        we don't have a sequential source and target city which aare the same. This is easier for support and is
        doing almost the same job. 
        """
        while True:
            job_indexes = [i for i, job in enumerate(jobs) if job is not None]
            if len(job_indexes) == 0:
                # No undone jobs left
                break

            for i in job_indexes:
                job = self.__execute_job(jobs[i], batch_size)
                if sum(job.resources) == 0:
                    job = None
                jobs[i] = job


    @staticmethod
    def optimize_jobs(jobs: List[TransportJob]) -> List[TransportJob]:
        """
        Optimizes routes by origin city
        """
        def get_key(_job: TransportJob):
            return '{}-{}'.format(_job.origin_city['id'], _job.target_city['id'])

        job_map = {}
        for job in jobs:
            key = get_key(job)
            _jobs = job_map.get(key, [])
            _jobs.append(job.resources)
            job_map[key] = _jobs

        res = []
        for job in jobs:
            key = get_key(job)
            _jobs = job_map[key]
            if _jobs is not None:
                res.append(TransportJob(
                    origin_city=job.origin_city,
                    target_city=job.target_city,
                    resources=[sum(pair) for pair in zip(*_jobs)]
                ))
            job_map[key] = None
        return res

    def __execute_job(self, job: TransportJob, batch_size: Union[int, None]) -> TransportJob:
        """
        Executes the transport job (even in batches)
        :param job: what to execute
        :return:
        """
        remaining_resources_to_send = job.resources
        storage_capacity_in_city = len(materials_names) * [sys.maxsize]

        remaining_str = ', '.join(['{}{}'.format(addThousandSeparator(volume), name[0])
                                   for volume, name in zip(remaining_resources_to_send, materials_names)])

        obj = f'Sending {remaining_str} ---> {job.target_city["name"]}'
        self._set_process_info(message=obj, target_city=job.origin_city["name"])

        ships_available = waitForAvailableShips(self.ikariam_service, self._wait)
        storage_capacity_in_ships = ships_available * self.MAXIMUM_SHIP_SIZE

        # Consider maximum batch size
        if batch_size is not None:
            storage_capacity_in_ships = min(storage_capacity_in_ships, batch_size)

        origin_city = getCity(self.ikariam_service.get(city_url + str(job.origin_city['id'])))
        target_city = getCity(self.ikariam_service.get(city_url + str(job.target_city['id'])))

        foreign = str(target_city['id']) != str(job.target_city['id'])
        if not foreign:
            storage_capacity_in_city = target_city['freeSpaceForResources']

        resources_to_send = []
        for remaining, available, capacity in zip(remaining_resources_to_send,
                                                  origin_city['availableResources'],
                                                  storage_capacity_in_city):
            minimum_resource_value = min(remaining, available, capacity, storage_capacity_in_ships)
            resources_to_send.append(minimum_resource_value)
            storage_capacity_in_ships -= minimum_resource_value

        total_resources_to_send = sum(resources_to_send)
        if total_resources_to_send == 0:
            # no space available in target city
            # no resources available in the origin city
            self._wait(
                SECONDS_IN_HOUR,
                'Either no space left in {} or no resources in {}. Will retry! Remaining {}'.format(
                    target_city['name'], origin_city['name'], remaining_str
                ),
                max_random=60
            )

        actually_sent_resources = self.__send_goods(origin_city, target_city, resources_to_send)
        if sum(actually_sent_resources) == 0:
            self._wait(
                seconds=30,
                info='Failed to send resources from {} to {}. Will try again!'.format(
                    origin_city['name'], target_city['name']
                ),
                max_random=20,
            )

        remaining_resources_to_send = [r - a for r, a in zip(remaining_resources_to_send, actually_sent_resources)]
        return TransportJob(job.origin_city, job.target_city, remaining_resources_to_send)

    def __send_goods(self, origin_city, target_city, resources_to_send):
        # this can fail if a random request is made in between this two posts

        # Change from the city the bot is sitting right now to the city we want to load resources from
        self.ikariam_service.post(
            noIndex=True,
            params={
                'action': 'header',
                'function': 'changeCurrentCity',
                'actionRequest': actionRequest,
                'oldView': 'city',
                'cityId': origin_city['id'],
                'backgroundView': 'city',
                'currentCityId': getCurrentCityId(self.ikariam_service),
                'ajax': '1'
            }
        )

        required_ships = int(math.ceil((Decimal(sum(resources_to_send)) / Decimal(self.MAXIMUM_SHIP_SIZE))))
        # Request to send the resources from the origin to the target
        data = {
            'action': 'transportOperations',
            'function': 'loadTransportersWithFreight',
            'destinationCityId': target_city['id'],
            'islandId': target_city['islandId'],
            'oldView': '',
            'position': '',
            'avatar2Name': '',
            'city2Name': '',
            'type': '',
            'activeTab': '',
            'transportDisplayPrice': '0',
            'premiumTransporter': '0',
            'transporters': required_ships,
            'capacity': '5',
            'max_capacity': '5',
            'jetPropulsion': '0',
            'backgroundView': 'city',
            'currentCityId': origin_city['id'],
            'templateView': 'transport',
            'currentTab': 'tabSendTransporter',
            'actionRequest': actionRequest,
            'ajax': '1'
        }

        # add amounts of resources to send
        for ind, res in enumerate(resources_to_send):
            key = 'cargo_resource' if ind == 0 else 'cargo_tradegood{:d}'.format(ind)
            data[key] = res

        resp = self.ikariam_service.post(params=data)
        resp = json.loads(resp, strict=False)
        if resp[3][1][0]['type'] == 10:
            return resources_to_send

        # we've failed to send them....
        return len(resources_to_send) * [0]


