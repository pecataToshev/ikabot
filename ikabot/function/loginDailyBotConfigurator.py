#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from ikabot.bot.loginDailyBot import LoginDailyBot
from ikabot.helpers.database import Database
from ikabot.helpers.gui import enter
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def login_daily_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    print('I will enter every day.')
    LoginDailyBot(ikariam_service, {}).start(
        action='Login Daily',
        objective='Login every 24h'
    )
    enter()
