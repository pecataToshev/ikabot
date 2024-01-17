#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.wineMonitoringBot import WineMonitoringBot
from ikabot.helpers.database import Database
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.userInput import read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def configure_wine_monitoring_bot(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    if not telegram.has_valid_data():
        print('Telegram data is required to setup the monitoring. Sorry!')
        enter()
        return

    hours = read(msg='How many hours should be left until the wine runs out in a city so that it\'s alerted?',
                 min=1, digit=True)
    print("You'll will be alerted when the wine runs out in less than {:d} hours in any city".format(hours))
    enter()

    WineMonitoringBot(ikariam_service, {'minimumWineHours': hours}).start(
        action='Monitor Wine',
        objective='Wine Hours {}'.format(hours),
    )
