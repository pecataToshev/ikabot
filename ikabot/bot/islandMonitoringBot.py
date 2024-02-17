#! /usr/bin/env python3
# -*- coding: utf-8 -*-
from enum import Enum
from math import ceil
from typing import Dict, List

from ikabot.bot.bot import Bot
from ikabot.config import island_url, materials_names
from ikabot.helpers.dicts import combine_dicts_with_lists, search_additional_keys_in_dict, search_value_change_in_dict
from ikabot.helpers.getJson import getIsland
from ikabot.helpers.gui import decodeUnicodeEscape
from ikabot.helpers.citiesAndIslands import getIslandsIds


class CityStatusUpdate(Enum):
    COLONY_STARTED_INITIALIZING = 'colony-started-initializing'
    COLONY_INITIALIZED = 'colony-initialized'
    COLONY_LEVEL_UP = 'colony-level-up'

    DISAPPEARED = 'disappeared'
    INACTIVATED = 'inactivated'
    RE_ACTIVATED = 're-activated'

    VACATION_WENT = 'vacation-went'
    VACATION_RETURNED = 'vacation-returned'

    FIGHT_STARTED = 'fight-started'
    FIGHT_STOPPED = 'fight-stopped'

    PIRACY_CREATED = 'piracy-created'
    PIRACY_REMOVED = 'piracy-removed'


class IslandMonitoringBot(Bot):
    __state_inactive = 'inactive'
    __state_vacation = 'vacation'

    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.specified_island_ids = bot_config['islandsToMonitor']
        self.waiting_minutes = bot_config['waitingMinutes']
        self.inform_list = bot_config['informList']

    def _get_process_info(self) -> str:
        return 'I monitor islands each {} minutes'.format(self.waiting_minutes)

    def _start(self) -> None:
        # this dict will contain all the cities from each island
        # as they were in last scan
        # {islandId: {cityId: city}}
        cities_before_per_island = {}

        while True:
            islands_ids = self.specified_island_ids
            if not islands_ids:
                # this is done inside the loop because the user may have colonized
                # a city in a new island
                islands_ids = getIslandsIds(self.ikariam_service)

            for island_id in islands_ids:
                island = getIsland(self.ikariam_service.get(island_url + island_id))
                # cities in the current island
                _cities_now = self.extract_cities(island)

                if island_id in cities_before_per_island:
                    _cities_before = dict(cities_before_per_island[island_id])
                    _updates = self.compare_island_cities(
                        cities_before=_cities_before,
                        cities_now=_cities_now,
                    )
                    _cities_before.update(_cities_now)
                    self.notify_updates(_updates, _cities_before)


                # update cities_before_per_island for the current island
                cities_before_per_island[island_id] = dict(_cities_now)

            self._wait(self.waiting_minutes * 60,
                       f'Checked islands {str([int(i) for i in islands_ids]).replace(" ", "")}')

    @staticmethod
    def extract_cities(island):
        """
        Extract the cities from island
        :param island: dict[]
        :return: dict[dict] cityId -> city
        """
        _res = {}

        _island_name = decodeUnicodeEscape(island['name'])
        for city in island['cities']:
            if city['type'] != 'city':
                continue

            city['islandX'] = island['x']
            city['islandY'] = island['y']
            city['tradegood'] = island['tradegood']
            city['material'] = materials_names[island['tradegood']]
            city['islandName'] = _island_name
            city['cityName'] = decodeUnicodeEscape(city['name'])
            city['ownerName'] = decodeUnicodeEscape(city['Name'])
            if city['AllyId'] > 0:
                city['allianceName'] = decodeUnicodeEscape(city['AllyTag'])
                city['hasAlliance'] = True
                city['player'] = "{} [{}]".format(city['ownerName'], city['allianceName'])
            else:
                city['alliance'] = ''
                city['hasAlliance'] = False
                city['player'] = city['ownerName']

            if 'avatarScores' in island and str(city['Id']) in island['avatarScores']:
                _ranking = island['avatarScores'][str(city['Id'])]
                city['playerPlace'] = _ranking['place']
                city['playerPoints'] = sum(ceil(int(x.replace(',', '')) / 100) for x in [
                    _ranking['building_score_main'],
                    _ranking['research_score_main'],
                    _ranking['army_score_main'],
                    _ranking['trader_score_secondary'] + '0',  # trader_score_secondary is more accurate when /10
                ])
                city['player'] = "{} (#{}, {})".format(
                    city['player'],
                    city['playerPlace'],
                    (str(city['playerPoints'] // 1000) + 'k') if city['playerPoints'] > 1000 else city['playerPoints']
                )

            _res[city['id']] = city

        return _res

    @staticmethod
    def monitor_level_up(
            cities_before: Dict[int, dict],
            cities_now: Dict[int, dict]
    ) -> Dict[int, List[CityStatusUpdate]]:
        res = {}
        for city_id, cn in cities_now.items():
            _was_there = city_id in cities_before
            if _was_there and cities_before[city_id]['level'] == cn['level']:
                continue

            _stat = CityStatusUpdate.COLONY_LEVEL_UP
            if cn['level'] == 0:
                _stat = CityStatusUpdate.COLONY_STARTED_INITIALIZING
            elif (not _was_there or cities_before[city_id]['level'] == 0) and cn['level'] > 0:
                _stat = CityStatusUpdate.COLONY_INITIALIZED

            res[city_id] = [_stat]

        return res

    @staticmethod
    def monitor_status_change(
            cities_before: Dict[int, dict],
            cities_now: Dict[int, dict]
    ) -> Dict[int, List[CityStatusUpdate]]:
        res = {}
        for city, state_before, state_now in search_value_change_in_dict(
                cities_before,
                cities_now,
                lambda c: c['state']
        ):
            _stat = []
            if state_before == IslandMonitoringBot.__state_vacation:
                _stat.append(CityStatusUpdate.VACATION_RETURNED)
            elif state_now == IslandMonitoringBot.__state_vacation:
                _stat.append(CityStatusUpdate.VACATION_WENT)

            if state_before == IslandMonitoringBot.__state_inactive:
                _stat.append(CityStatusUpdate.RE_ACTIVATED)
            elif state_now == IslandMonitoringBot.__state_inactive:
                _stat.append(CityStatusUpdate.INACTIVATED)

            res[city['id']] = _stat

        return res

    @staticmethod
    def monitor_fights(
            cities_before: Dict[int, dict],
            cities_now: Dict[int, dict]
    ) -> Dict[int, List[CityStatusUpdate]]:
        res = {}
        for city, _before_army_action, _now_army_action in search_value_change_in_dict(
                cities_before,
                cities_now,
                lambda c: c.get('infos', {}).get('armyAction', None)
        ):
            _stat = None
            if _now_army_action == 'fight':
                _stat = CityStatusUpdate.FIGHT_STARTED
            elif _before_army_action == 'fight':
                _stat = CityStatusUpdate.FIGHT_STOPPED

            if _stat is not None:
                res[city['id']] = [_stat]

        return res

    @staticmethod
    def monitor_piracy(
            cities_before: Dict[int, dict],
            cities_now: Dict[int, dict]
    ) -> Dict[int, List[CityStatusUpdate]]:
        res = {}
        for city, _before_piracy, _now_piracy in search_value_change_in_dict(
                cities_before,
                cities_now,
                lambda c: c.get('actions', {}).get('piracy_raid', 0)
        ):
            _stat = None
            if _before_piracy == 0:
                _stat = CityStatusUpdate.PIRACY_CREATED
            elif _now_piracy == 0:
                _stat = CityStatusUpdate.PIRACY_REMOVED

            if _stat is not None:
                res[city['id']] = [_stat]

        return res

    @staticmethod
    def compare_island_cities(
            cities_before: Dict[int, dict],
            cities_now: Dict[int, dict]
    ) -> Dict[int, List[CityStatusUpdate]]:

        return combine_dicts_with_lists([
            {cid: [CityStatusUpdate.DISAPPEARED] for cid in search_additional_keys_in_dict(cities_before, cities_now)},
            IslandMonitoringBot.monitor_level_up(cities_before, cities_now),
            IslandMonitoringBot.monitor_status_change(cities_before, cities_now),
            IslandMonitoringBot.monitor_fights(cities_before, cities_now),
            IslandMonitoringBot.monitor_piracy(cities_before, cities_now),
        ])

    def notify_updates(self, updates: Dict[int, List[CityStatusUpdate]], cities: Dict[int, dict]) -> None:
        for city_id, status_updates in updates.items():
            _messages = self.prepare_messages(status_updates)
            for _msg in _messages:
                _msg += ' on [{islandX}:{islandY}] {islandName} ({material})'
                self.telegram.send_message(_msg.format(**cities[city_id]))

    @staticmethod
    def prepare_messages(status_updates: List[CityStatusUpdate]) -> List[str]:
        if CityStatusUpdate.DISAPPEARED in status_updates:
            return ['The city {cityName} of {player} disappeared']

        _res = []

        # missing the level up notification
        if CityStatusUpdate.COLONY_INITIALIZED in status_updates:
            _res.append('The city {cityName} of {player} has reached level 1')
        elif CityStatusUpdate.COLONY_STARTED_INITIALIZING in status_updates:
            _res.append('{player} has reserved city spot')

        if CityStatusUpdate.VACATION_RETURNED in status_updates:
            _res.append('{player} has returned from vacation with the city {cityName}')
        elif CityStatusUpdate.VACATION_WENT in status_updates:
            _res.append('{player} went on vacation with the city {cityName}')

        if CityStatusUpdate.RE_ACTIVATED in status_updates:
            _res.append('{player} became active again with the city {cityName}')
        elif CityStatusUpdate.INACTIVATED in status_updates:
            _res.append('{player} became INACTIVE with the city {cityName}')

        if CityStatusUpdate.FIGHT_STARTED in status_updates:
            _res.append('A fight has started in the city {cityName} of the {player}')
        elif CityStatusUpdate.FIGHT_STOPPED in status_updates:
            _res.append('The fight has ended in the city {cityName} of the {player}')

        if CityStatusUpdate.PIRACY_CREATED in status_updates:
            _res.append('The city {cityName} of {player} can pirate now')
        elif CityStatusUpdate.PIRACY_REMOVED in status_updates:
            _res.append('The city {cityName} of {player} can no longer pirate')

        return _res
