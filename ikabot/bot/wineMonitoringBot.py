import logging
from decimal import Decimal
from typing import List

from ikabot.bot.bot import Bot
from ikabot.config import city_url, SECONDS_IN_HOUR
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import bcolors, daysHoursMinutes
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.resources import getProductionPerSecond


class WineMonitoringBot(Bot):
    __process_info_working = 'Checking for low wine'

    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.minimum_available_wine_seconds = int(bot_config['minimumWineHours']) * SECONDS_IN_HOUR

    def _get_process_info(self) -> str:
        return '\nI alert if the wine runs out in less than {} hours\n'.format(self.bot_config['minimumWineHours'])

    def _start(self) -> None:
        alert_was_triggered = {}
        while True:
            __problems: List[List[str]] = []
            self._set_process_info(self.__process_info_working)
    
            # getIdsOfCities is called on a loop because the amount of cities may change
            _, cities = getIdsOfCities(self.ikariam_service)
            for city_id in cities:
                logging.debug('Checking city: %s', city_id)
                city = getCity(self.ikariam_service.get(city_url + city_id))
                self._set_process_info(self.__process_info_working, target_city=city['name'])

                consumption_per_hour = city['wineConsumptionPerHour']
                was_alerted = alert_was_triggered.get(city_id, False)

                # is a wine city
                if cities[city_id]['tradegood'] == '1':
                    wine_production = getProductionPerSecond(self.ikariam_service, city_id)[1] * SECONDS_IN_HOUR
                    if consumption_per_hour > wine_production:
                        consumption_per_hour -= wine_production
                    else:
                        alert_was_triggered[city_id] = False
                        continue
    
                if consumption_per_hour == 0:
                    logging.debug('No wine consumption in %s', city['name'])
                    __problems.append([bcolors.WARNING, city['name'], 'noConsumption'])
                    if not was_alerted:
                        msg = 'The city {} is not consuming wine!'.format(city['name'])
                        self.telegram.send_message(msg)
                        alert_was_triggered[city_id] = True
                    continue

                consumption_per_sec = Decimal(consumption_per_hour) / Decimal(SECONDS_IN_HOUR)
                wine_available = city['availableResources'][1]
                seconds_left = Decimal(wine_available) / Decimal(consumption_per_sec)

                logging.debug('Wine left in %s for %s', city['name'], daysHoursMinutes(int(seconds_left)))

                if seconds_left < self.minimum_available_wine_seconds:
                    time_left = daysHoursMinutes(int(seconds_left))
                    __problems.append([bcolors.RED, city['name'], time_left])
                    if was_alerted is False:
                        msg = 'In {}, the wine will run out in {}'.format(time_left, city['name'])
                        self.telegram.send_message(msg)
                        alert_was_triggered[city_id] = True
                else:
                    alert_was_triggered[city_id] = False

            self._set_process_info('Finished checking for low wine', target_city='')

            __msg = bcolors.GREEN + 'No alerts'
            if len(__problems) > 0:
                __msg = '{}Alerts{}: [{}{}]'.format(
                    bcolors.WARNING,
                    bcolors.ENDC,
                    bcolors.ENDC + ', '.join("{}{}: {}".format(*p) for p in __problems),
                    bcolors.ENDC,
                )

            self._wait(20*60, __msg + bcolors.ENDC)
