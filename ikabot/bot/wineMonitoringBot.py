from decimal import Decimal

from ikabot.bot.bot import Bot
from ikabot.config import city_url, SECONDS_IN_HOUR
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import daysHoursMinutes
from ikabot.helpers.pedirInfo import getIdsOfCities
from ikabot.helpers.resources import getProductionPerSecond


class WineMonitoringBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.minimum_available_wine_seconds = int(bot_config['minimumWineHours']) * SECONDS_IN_HOUR

    def _get_process_info(self) -> str:
        return '\nI alert if the wine runs out in less than {} hours\n'.format(self.bot_config['minimumWineHours'])

    def _start(self) -> None:
        alert_was_triggered = {}
        while True:
            self._set_process_info('Checking for low wine')
    
            # getIdsOfCities is called on a loop because the amount of cities may change
            ids, cities = getIdsOfCities(self.ikariam_service)
            for city_id in cities:
                city = getCity(self.ikariam_service.get(city_url + city_id))
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
                    if not was_alerted:
                        msg = 'The city {} is not consuming wine!'.format(city['name'])
                        self.telegram.send_message(msg)
                        alert_was_triggered[city_id] = True
                    continue

                consumption_per_seg = Decimal(consumption_per_hour) / Decimal(SECONDS_IN_HOUR)
                wine_available = city['availableResources'][1]
                seconds_left = Decimal(wine_available) / Decimal(consumption_per_seg)
                if seconds_left < self.minimum_available_wine_seconds:
                    if was_alerted is False:
                        time_left = daysHoursMinutes(int(seconds_left))
                        msg = 'In {}, the wine will run out in {}'.format(time_left, city['name'])
                        self.telegram.send_message(msg)
                        alert_was_triggered[city_id] = True
                else:
                    alert_was_triggered[city_id] = False
    
            self.ikariam_service.wait(20*60, 'I wait for the next check')
