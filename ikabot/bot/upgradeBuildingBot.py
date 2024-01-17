import logging
import time

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url
from ikabot.helpers.getJson import getCity
from ikabot.helpers.planRoutes import getMinimumWaitingTime


class UpgradeBuildingBot(Bot):
    """
    Upgrades building and transport resources automatically
    """
    __MAXIMUM_FAILED_WAITING_TIMES_ATTEMPTS = 3
    __SLEEP_DURATION_BETWEEN_FAILED_WAIT_TIMES = 20

    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.city_id = bot_config['cityId']
        self.city_name = bot_config['cityName']

        building = bot_config['building']
        self.building_name = building['name']
        self.building_name_and_position = building['positionAndName']
        self.building_building = building['building']
        self.building_target_level = building['targetLevel']
        self.building_position = building['position']

        self.transport_resources_pid = bot_config.get('transportResourcesPid', None)

    def _get_process_info(self):
        return '\nI upgrade {} from {} to {} level in {}\n'.format(
            self.building_name_and_position,
            self.bot_config['buildingCurrentLevel'],
            self.building_target_level,
            self.city_name,
        )

    def _start(self) -> None:
        if self.__upgrade_building_bot():
            # We've successfully finished the job
            if self.bot_config.get('notifyWhenDone', False):
                self.telegram.send_message("I've started upgrading {} to {} in {}".format(
                    self.building_name_and_position, self.building_target_level, self.city_name
                ))
            return

        # We've failed


        print('a')

    @staticmethod
    def get_building_level(building):
        current_level = building['level']
        if building['isBusy']:
            current_level += 1
        return current_level

    @staticmethod
    def __get_currently_expanding_building(city):
        """
        Returns currently expanding building
        :param city: dict[]
        :return: dict[]/None
        """
        buildings_in_construction = [building for building in city['position'] if 'completed' in building]
        if len(buildings_in_construction) == 0:
            return None

        return buildings_in_construction[0]

    @staticmethod
    def __get_waiting_time_to_finish_building(building):
        if building is None or 'completed' not in building:
            return 0

        return time.time() - int(building['completed'])

    def __upgrade_building_bot(self):
        """
        Performs the upgrade logic loop
        :return: bool -> is successful
        """
        failed_consecutive_wait_times = 0
        while True:
            city = getCity(self.ikariam_service.get(city_url + self.city_id))
            building = city['position'][self.building_position]

            self.__validate_building(building)
            if not self.__has_more_levels_to_upgrade(building):
                # We've successfully finished the job
                return True

            logging.info('city: %s', city)
            building_in_construction = self.__get_currently_expanding_building(city)
            if building_in_construction is None and building['canUpgrade']:
                self.__expand_building(building)

                # check if the upgrade has started
                city = getCity(self.ikariam_service.get(city_url + self.city_id))
                building_in_construction = self.__get_currently_expanding_building(city)
                if (building_in_construction is None
                        or building_in_construction['position'] != self.building_position
                        or building_in_construction['building'] != self.building_building):
                    raise Exception("Failed to extend building {} to {} in {}".format(
                        self.building_name_and_position,
                        self.get_building_level(building) + 1,
                        self.city_name
                    ))

                # add check for started expansion logic
                continue  # Check if we need to upgrade more levels or we can skip the sleep

            waiting_times = self.__get_waiting_times_with_reason(building_in_construction)
            if len(waiting_times) == 0:
                failed_consecutive_wait_times += 1
                if failed_consecutive_wait_times > self.__MAXIMUM_FAILED_WAITING_TIMES_ATTEMPTS:
                    raise Exception('I failed {} times to get waiting time. '
                                    'Something is wrong...'.format(failed_consecutive_wait_times))
                self._wait(
                    self.__SLEEP_DURATION_BETWEEN_FAILED_WAIT_TIMES,
                    'Failed to get adequate waiting times {}/{}. Will try again'.format(
                        failed_consecutive_wait_times, self.__MAXIMUM_FAILED_WAITING_TIMES_ATTEMPTS
                    )
                )
                continue

            failed_consecutive_wait_times = 0
            [waiting_time, waiting_reason] = min(waiting_times, key=lambda x: x[0])
            self._wait(waiting_time, waiting_reason, 10)

    def __get_waiting_times_with_reason(self, building_in_construction):
        waiting_times = []
        minimal_fleet_arriving_time = getMinimumWaitingTime(self.ikariam_service)
        if minimal_fleet_arriving_time > 0:
            waiting_times.append([
                minimal_fleet_arriving_time,
                'Waiting some fleet to arrive'
            ])

        if self.transport_resources_pid is not None:
            _process = self.db.get_processes({'pid': self.transport_resources_pid})
            if len(_process) == 0:
                # we no-longer have this process running
                self.transport_resources_pid = None
            else:
                next_action_time = _process[0].get('nextActionTime', None)
                if next_action_time is not None:
                    waiting_times.append([
                        next_action_time - time.time(),
                        'Waiting next action of transporting resources (pid: {})'.format(self.transport_resources_pid)
                    ])
                else:
                    waiting_times.append([
                        30,
                        "We're in race condition with the process for"
                        " transporting resources (pid: {})".format(self.transport_resources_pid)
                    ])

        building_upgrade_time_left = self.__get_waiting_time_to_finish_building(building_in_construction)
        if building_upgrade_time_left > 0:
            waiting_times.append([
                building_upgrade_time_left,
                'Waiting {} to get to level {}'.format(
                    building_in_construction['positionAndName'],
                    self.get_building_level(building_in_construction)
                )
            ])
        logging.info("Figuring out why it is not working: minimal_fleet_arriving_time:%s, transport_resources_pid:%s, building_in_construction:%s, building_upgrade_time_left:%s",
                     minimal_fleet_arriving_time, self.transport_resources_pid, building_in_construction, building_upgrade_time_left)
        return waiting_times

    def __validate_building(self, building):
        if self.building_building != building['building']:
            raise Exception('Different building on this position. '
                            'Have you changed something via UI? Expected {} but found {}'.format(
                self.building_name, building['name']
            ))
    def __has_more_levels_to_upgrade(self, building):
        return self.get_building_level(building) < self.building_target_level

    def __expand_building(self, building):
        self.ikariam_service.post(
            noIndex=True,
            params={
                'action': 'CityScreen',
                'function': 'upgradeBuilding',
                'actionRequest': actionRequest,
                'cityId': self.city_id,
                'position': self.building_position,
                'level': building['level'],
                'activeTab': 'tabSendTransporter',
                'backgroundView': 'city',
                'currentCityId': self.city_id,
                'templateView': building['building'],
                'ajax': '1'
            }
        )