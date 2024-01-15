#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.attacksMonitoringBot import AttacksMonitoringBot
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.pedirInfo import read


def configure_alert_attacks_monitoring_bot(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()

    if not telegram.has_valid_data():
        print('Telegram data is required to setup the monitoring. Sorry!')
        enter()
        return

    default = 20
    minutes = read(msg='How often should I search for attacks?(min:3, default: {:d}): '.format(default), min=3,
                   default=default)
    print('I will check for attacks every {:d} minutes'.format(minutes))
    enter()

    AttacksMonitoringBot(ikariam_service, {'waitMinutes': minutes}).start(
        action='Monitor Attacks',
        objective='Every {} minutes'.format(minutes),
    )
