import logging

from ikabot.bot.upgradeBuilding.abstractUpgradeBuildingBot import AbstractUpgradeBuildingBot


class UpgradeSingleBuildingBot(AbstractUpgradeBuildingBot):
    """
    Upgrades single building and waits for transported resources automatically
    """

    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        building = bot_config['building']
        self.building_name = building['name']
        self.building_name_and_position = building['positionAndName']
        self.building_building = building['building']
        self.building_target_level = building['targetLevel']
        self.building_position = building['position']

    def _get_process_info(self):
        return '\nI upgrade {} from {} to {} level in {}\n'.format(
            self.building_name_and_position,
            self.bot_config['buildingCurrentLevel'],
            self.building_target_level,
            self.city_name,
        )

    def _get_building_to_upgrade(self, city: dict) -> dict:
        _building = city['position'][self.building_position]
        if self.building_building != _building['building']:
            logging.debug("Different building on this position. Expected %s but found %s",
                          self.building_building, _building['building'])
            raise Exception('Different building on this position. '
                            'Have you changed something via UI? Expected {} but found {}'.format(
                self.building_name, _building['name']
            ))

        return _building

    def _notify_done_message(self) -> str:
        return "I've started upgrading {} to {} in {}".format(
            self.building_name_and_position, self.building_target_level, self.city_name
        )

    def _has_more_levels_to_upgrade(self, city, building):
        return self.get_building_level(building) < self.building_target_level
