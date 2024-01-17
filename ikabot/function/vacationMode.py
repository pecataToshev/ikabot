#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from ikabot.config import actionRequest
from ikabot.helpers.gui import banner, clear, enter
from ikabot.helpers.citiesAndIslands import getCurrentCityId
from ikabot.helpers.userInput import askUserYesNo


def activateVacationMode(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    current_city_id = getCurrentCityId(ikariam_service)

    ikariam_service.post(
        params={
            'action': 'Options',
            'function': 'activateVacationMode',
            'actionRequest': actionRequest,
            'backgroundView': 'city',
            'currentCityId': current_city_id,
            'templateView': 'options_umod_confirm'
        },
        ignoreExpire=True
    )


def vacationMode(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()
    if not askUserYesNo('Activate vacation mode'):
        return

    activateVacationMode(ikariam_service)
    print('Vacation mode has been activated.')
    enter()

    clear()
    sys.exit()
