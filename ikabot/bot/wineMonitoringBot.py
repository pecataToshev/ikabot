import logging
import time
from decimal import Decimal
from typing import List, Optional

from ikabot.bot.bot import Bot
from ikabot.config import SECONDS_IN_HOUR, city_url
from ikabot.helpers.citiesAndIslands import getIdsOfCities
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import Colours, daysHoursMinutes
from ikabot.helpers.resources import getProductionPerSecond


class WineMonitoringBot(Bot):
    __process_info_working = 'Checking for low wine'

    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.minimum_available_wine_seconds = int(bot_config['minimumWineHours']) * SECONDS_IN_HOUR

    def _get_process_info(self) -> str:
        return '\nI alert if the wine runs out in less than {} hours\n'.format(self.bot_config['minimumWineHours'])

    def _start(self) -> None:
        # Dictionary to store city_id -> timestamp (or None if no issue)
        # timestamp = when the threshold was first reached
        # None = no issue detected
        alert_timestamps = {}
        
        while True:
            __problems: List[List[str]] = []
            self._set_process_info(self.__process_info_working)
    
            # getIdsOfCities is called on a loop because the amount of cities may change
            _, cities = getIdsOfCities(self.ikariam_service)
            current_time = time.time()
            
            for city_id in cities:
                logging.debug('Checking city: %s', city_id)
                city = getCity(self.ikariam_service.get(city_url + city_id))
                self._set_process_info(self.__process_info_working, target_city=city['name'])

                consumption_per_hour = city['wineConsumptionPerHour']
                alert_timestamp: Optional[float] = alert_timestamps.get(city_id, None)

                # is a wine city
                if cities[city_id]['tradegood'] == '1':
                    wine_production = getProductionPerSecond(self.ikariam_service, city_id)[1] * SECONDS_IN_HOUR
                    if consumption_per_hour > wine_production:
                        consumption_per_hour -= wine_production
                    else:
                        # Issue resolved: wine production is sufficient
                        alert_timestamps[city_id] = None
                        continue
    
                if consumption_per_hour == 0:
                    logging.debug('No wine consumption in %s', city['name'])
                    __problems.append([Colours.Text.Light.YELLOW, city['name'], 'noConsumption'])
                    
                    # Check if we need to send/resend alert
                    should_alert = alert_timestamp is None or (current_time - alert_timestamp >= 24 * SECONDS_IN_HOUR)
                    
                    if should_alert:
                        msg = 'The city {} is not consuming wine!'.format(city['name'])
                        self.telegram.send_message(msg)
                        alert_timestamps[city_id] = current_time
                    continue

                consumption_per_sec = Decimal(consumption_per_hour) / Decimal(SECONDS_IN_HOUR)
                wine_available = city['availableResources'][1]
                seconds_left = Decimal(wine_available) / Decimal(consumption_per_sec)

                logging.debug('Wine left in %s for %s', city['name'], daysHoursMinutes(int(seconds_left)))

                if seconds_left < self.minimum_available_wine_seconds:
                    time_left = daysHoursMinutes(int(seconds_left))
                    __problems.append([Colours.Text.Light.RED, city['name'], time_left])
                    
                    # Check if we need to send/resend alert (first time or 24h passed)
                    should_alert = alert_timestamp is None or (current_time - alert_timestamp >= 24 * SECONDS_IN_HOUR)
                    
                    if should_alert:
                        msg = 'In {}, the wine will run out in {}'.format(city['name'], time_left)
                        self.telegram.send_message(msg)
                        alert_timestamps[city_id] = current_time
                else:
                    # Issue resolved: wine is above threshold
                    alert_timestamps[city_id] = None

            self._set_process_info('Finished checking for low wine', target_city='')

            __msg = Colours.Text.Light.GREEN + 'No alerts'
            if len(__problems) > 0:
                __msg = '{}Alerts{}: [{}{}]'.format(
                    Colours.Text.Light.YELLOW,
                    Colours.Text.RESET,
                    Colours.Text.RESET + ', '.join("{}{}: {}".format(*p) for p in __problems),
                    Colours.Text.RESET,
                )

            self._wait(SECONDS_IN_HOUR, __msg + Colours.Text.RESET)
