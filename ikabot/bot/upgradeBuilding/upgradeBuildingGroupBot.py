import logging
from abc import abstractmethod

from ikabot.bot.upgradeBuilding.abstractUpgradeBuildingBot import AbstractUpgradeBuildingBot


class UpgradeBuildingGroupBot(AbstractUpgradeBuildingBot):
    """
    Upgrades single building and waits for transported resources automatically
    """

    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.building_target_level = bot_config['targetLevel']
        building = bot_config['building']
        self.building_name = building['name']
        self.building_building = building['building']

    def _get_process_info(self):
        return '\nI upgrade all {} to {} level in {}\n'.format(
            self.building_name,
            self.building_target_level,
            self.city_name,
        )

    @staticmethod
    def _get_building_with_smallest_level_from_type(city: dict, building_type: str) -> dict:
        min_level = 10000
        position = None
        for building in city['position']:
            if building['building'] == building_type and building['level'] < min_level:
                min_level = building['level']
                position = building['position']

        if position is None:
            raise Exception('No {} found in {}'.format(building_type, city['name']))

        return city['position'][position]

    def _get_building_to_upgrade(self, city: dict) -> dict:
        return self._get_building_with_smallest_level_from_type(city, self.building_building)

    def _notify_done_message(self) -> str:
        return "I've started upgrading last {} to {} in {}".format(
            self.building_name, self.building_target_level, self.city_name
        )

    def _has_more_levels_to_upgrade(self, building):
        return self.get_building_level(building) < self.building_target_level
