#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

from ikabot.config import actionRequest
from ikabot.helpers.gui import getCurrentCityId


def getAvailableShips(session):
    """Function that returns the total number of free (available) ships
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
        Session object

    Returns
    -------
    ships : int
        number of currently available ships
    """
    html = session.get()
    return int(re.search(r'GlobalMenu_freeTransporters">(\d+)<', html).group(1))


def getTotalShips(session):
    """Function that returns the total number of ships, regardless of if they're available or not
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
        Session object

    Returns
    -------
    ships : int
        total number of ships the player has
    """
    html = session.get()
    return int(re.search(r'maxTransporters">(\d+)<', html).group(1))


def get_military_and_see_movements(ikariam_service, city_id=None):
    """
    Get current military movements
    :param ikariam_service:
    :param city_id: int/None
    :return:
    """
    if city_id is None:
        city_id = getCurrentCityId(ikariam_service)

    query = {
        'view': 'militaryAdvisor',
        'oldView': 'updateGlobalData',
        'cityId': city_id,
        'backgroundView': 'city',
        'currentCityId': city_id,
        'templateView': 'militaryAdvisor',
        'actionRequest': actionRequest,
        'ajax': 1
    }

    resp = ikariam_service.post(params=query)
    resp = json.loads(resp, strict=False)
    return resp[1][1][2]['viewScriptParams']['militaryAndFleetMovements']
