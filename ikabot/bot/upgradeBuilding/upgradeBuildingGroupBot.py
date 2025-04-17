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
        self.building_types = bot_config['buildingTypes']

    def _get_process_info(self):
        return '\nI upgrade all {} to {} level in {}\n'.format(
            self.building_types,
            self.building_target_level,
            self.city_name,
        )

    @staticmethod
    def _get_building_with_smallest_level_from_type(city: dict, building_type: [str]) -> dict:
        min_level = 10000
        position = None
        for building in city['position']:
            if (building['building'] in building_type
                    and AbstractUpgradeBuildingBot.get_building_level(building) < min_level
                    and building['isMaxLevel'] is False):
                min_level = AbstractUpgradeBuildingBot.get_building_level(building)
                position = building['position']

        if position is None:
            raise Exception('No {} found in {}'.format(building_type, city['name']))

        return city['position'][position]

    def _get_building_to_upgrade(self, city: dict) -> dict:
        return self._get_building_with_smallest_level_from_type(city, self.building_types)

    def _notify_done_message(self) -> str:
        return "I've started upgrading last {} to {} in {}".format(
            self.building_types, self.building_target_level, self.city_name
        )

    def _has_more_levels_to_upgrade(self, city: dict, building: dict) -> bool:
        _smallest_buildings = self._get_building_to_upgrade(city)
        return self.get_building_level(_smallest_buildings) < self.building_target_level
