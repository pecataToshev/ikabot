import logging

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url, SECONDS_IN_HOUR
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import addThousandSeparator


class ConductExperimentBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.number_of_experiments = int(bot_config['numberOfExperiments'])
        self.executed_experiments = 0
        self.city_id = bot_config["cityID"]
        self.city_name = bot_config["cityName"]
        self.academy_position = bot_config['academyPosition']

    def _get_process_info(self) -> str:
        return f'Process: Experiments\nWill execute {self.number_of_experiments} experiments with 4h cooldown'

    def _start(self) -> None:
        while True:

            # Validate if material is still there. If not - log it and send it via bot
            city = getCity(self.ikariam_service.get(city_url + str(self.city_id)))
            current_glass = int(city['availableResources'][3])

            if (current_glass < 300000):
                self.telegram.send_message(f"Experiment process ended on {self.city_name} due lack "
                                           f"of glass ({addThousandSeparator(current_glass)})")
                break

            self.ikariam_service.post(
                params={
                    'action': 'CityScreen',
                    'function': 'buyResearch',
                    'cityId': self.city_id,
                    'position': self.academy_position,
                    'backgroundView': 'city',
                    'currentCityId': self.city_id,
                    'templateView': 'academy',
                    'actionRequest': actionRequest,
                    'ajax': '1'
                }
            )
            self.executed_experiments += 1
            logging.info("Experiment done on %s; %s remaining",
                         self.city_name,
                         self.number_of_experiments - self.executed_experiments)

            if (self.executed_experiments >= self.number_of_experiments):
                break

            self._wait(
                info=f'Executing experiment #{self.executed_experiments} from {self.number_of_experiments}',
                seconds=4 * SECONDS_IN_HOUR + 5,
                max_random=120
            )
