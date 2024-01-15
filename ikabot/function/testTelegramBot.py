#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.helpers.gui import enter
from ikabot.helpers.pedirInfo import read


def testTelegramBot(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    input = read(msg='Enter the massage you wish to see: ')
    telegram.send_message(input)

    print('Sent message:', input)
    enter()
