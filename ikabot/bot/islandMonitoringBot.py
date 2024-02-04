#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.bot import Bot
from ikabot.config import island_url, materials_names
from ikabot.helpers.getJson import getIsland
from ikabot.helpers.gui import decodeUnicodeEscape
from ikabot.helpers.citiesAndIslands import getIslandsIds


class IslandMonitoringBot(Bot):
    inform_fights = 'inform-fights'
    inform_inactive = 'inform-inactive'
    inform_vacation = 'inform-vacation'
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
                cities_now = self.__extract_cities(island)

                if island_id in cities_before_per_island:
                    self.__compare_island_cities(
                        cities_before=cities_before_per_island[island_id],
                        cities_now=cities_now,
                    )

                # update cities_before_per_island for the current island
                cities_before_per_island[island_id] = dict(cities_now)

            self._wait(self.waiting_minutes * 60,
                       f'Checked islands {str([int(i) for i in islands_ids]).replace(" ", "")}')

    @staticmethod
    def __extract_cities(island):
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

            _res[city['id']] = city

        return _res

    def __compare_island_cities(self, cities_before, cities_now):
        """
        Parameters
        ----------
        cities_before : dict[dict]
            A dict of cities on the island on the previous check
        cities_now : dict[dict]
            A dict of cities on the island on the current check
        """
        __island_info = ' on [{islandX}:{islandY}] {islandName} ({material})'

        # someone disappeared
        for disappeared_id in self.__search_additional_keys(cities_before, cities_now):
            msg = 'The city {cityName} of {player} disappeared' + __island_info
            self.telegram.send_message(msg.format(**cities_before[disappeared_id]))

        # someone colonised
        for colonized_id in self.__search_additional_keys(cities_now, cities_before):
            msg = 'Player {player} created a new city {cityName}' + __island_info
            self.telegram.send_message(msg.format(**cities_now[colonized_id]))

        if self.inform_inactive in self.inform_list:
            for city, state_before, state_now in self.__search_state_change(
                    cities_before,
                    cities_now,
                    lambda c: c['state']
            ):
                if state_before == self.__state_inactive:
                    _status = 'active again'
                elif state_now == self.__state_inactive:
                    _status = 'inactive'
                else:
                    continue

                msg = ('The player {player} with the city {cityName} '
                       'became {status}!') + __island_info
                self.telegram.send_message(msg.format(status=_status, **city))

        if self.inform_vacation in self.inform_list:
            for city, state_before, state_now in self.__search_state_change(
                    cities_before,
                    cities_now,
                    lambda c: c['state']
            ):
                if state_before == self.__state_vacation:
                    _status = 'returned from'
                elif state_now == self.__state_vacation:
                    _status = 'went on'
                else:
                    continue

                msg = ('The player {player} with the city {cityName} '
                       '{status} vacation!') + __island_info

                self.telegram.send_message(msg.format(status=_status, **city))

        if self.inform_fights in self.inform_list:
            for city, _before_army_action, _now_army_action in self.__search_state_change(
                    cities_before,
                    cities_now,
                    lambda c: c.get('infos', {}).get('armyAction', None)
            ):

                if _now_army_action == 'fight':
                    _fight_status = 'started'
                elif _before_army_action == 'fight':
                    _fight_status = 'stopped'
                else:
                    continue

                msg = ('A fight {fightStatus} in the city {cityName} '
                       'of the player {player}') + __island_info
                self.telegram.send_message(msg.format(fightStatus=_fight_status, **city))

    @staticmethod
    def __search_additional_keys(source, target):
        """
        Search for keys that were in source but are not in the target dictionary
        :param source: dict[dict]
        :param target: dict[dict]
        :return: list[int] ids of the additional keys in the source
        """
        return [k for k in source.keys() if k not in target]

    @staticmethod
    def __search_state_change(cities_before, cities_now, state_getter):
        """
        Searches for change in state between cities_before and cities_now with the
        state_getter function.
        Returns list of changes (city, old_state, new_state)
        !!!IMPORTANT!!! old_state != new_state
        :param cities_before: dict[dict[]]
        :param cities_now:    dict[dict[]]
        :param state_getter:  dict[] -> string
        :return: list[[city_now, old_state, new_state]]
        """
        _res = []
        for city_id, city_before in cities_before.items():
            city_now = cities_now.get(city_id, None)
            if city_now is None:
                continue

            _state_before = state_getter(city_before)
            _state_now = state_getter(city_now)
            if _state_before != _state_now:
                _res.append([city_now, _state_before, _state_now])

        return _res
