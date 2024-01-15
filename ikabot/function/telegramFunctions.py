#! /usr/bin/env python3
# -*- coding: utf-8 -*-
from ikabot.helpers.database import Database
from ikabot.helpers.gui import enter
from ikabot.helpers.pedirInfo import read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def test_telegram_bot(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    input = read(msg='Enter the massage you wish to see: ')
    telegram.send_message(input)

    print('Sent message:', input)
    enter()


def update_telegram_bot(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    telegram.update_data()
