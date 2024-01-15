#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url, SECONDS_IN_HOUR
from ikabot.helpers.gui import getDateTime
from ikabot.helpers.pedirInfo import getIdsOfCities


class LoginDailyBot(Bot):

    def _get_process_info(self) -> str:
        return 'I enter every day'

    def _start(self) -> None:
        while True:
            (ids, cities) = getIdsOfCities(self.ikariam_service)
            for id in ids:
                html = self.ikariam_service.post(city_url + str(id))
                if 'class="fountain' in html:
                    url = 'action=AvatarAction&function=giveDailyActivityBonus&dailyActivityBonusCitySelect={0}&startPageShown=1&detectedDevice=1&autoLogin=on&cityId={0}&activeTab=multiTab2&backgroundView=city&currentCityId={0}&actionRequest={1}&ajax=1'.format(id, actionRequest)
                    self.ikariam_service.post(url)
                    if 'class="fountain_active' in html:
                        url = 'action=AmbrosiaFountainActions&function=collect&backgroundView=city&currentCityId={0}&templateView=ambrosiaFountain&actionRequest={1}&ajax=1'.format(id, actionRequest)
                        self.ikariam_service.post(url)
                    break

            self._wait(
                24*SECONDS_IN_HOUR,
                max_random=60,
                info=f'Last login @{getDateTime()}',
            )
