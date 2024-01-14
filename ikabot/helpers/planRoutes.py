#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import random
import re

from ikabot.config import actionRequest
from ikabot.helpers.naval import getAvailableShips


def get_random_wait_time():
    return random.randint(0, 20) * 3


def getMinimumWaitingTime(session):
    """This function returns the time needed to wait for the closest fleet to arrive. If all ships are unavailable,
    this represents the minimum time needed to wait for any ships to become available.
    A random waiting time between 0 and 10 seconds is added to the waiting time to avoid race conditions between
    multiple concurrently running processes.
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
        Session object

    Returns
    -------
    timeToWait : int
        the minimum waiting time for the closest fleet to arrive
    """
    html = session.get()
    idCiudad = re.search(r'currentCityId:\s(\d+),', html).group(1)
    url = 'view=militaryAdvisor&oldView=city&oldBackgroundView=city&backgroundView=city&currentCityId={}&actionRequest={}&ajax=1'.format(
        idCiudad, actionRequest)
    posted = session.post(url)
    postdata = json.loads(posted, strict=False)
    militaryMovements = postdata[1][1][2]['viewScriptParams']['militaryAndFleetMovements']
    current_time = int(postdata[0][1]['time'])
    delivered_times = []
    for militaryMovement in [mv for mv in militaryMovements if mv['isOwnArmyOrFleet']]:
        remaining_time = int(militaryMovement['eventTime']) - current_time
        delivered_times.append(remaining_time)
    if delivered_times:
        return min(delivered_times) + get_random_wait_time()
    else:
        return 0


def waitForAvailableShips(session, wait):
    """This function will return the number of available ships, and if there aren't any, it will wait for the closest fleet to arrive and then return the number of available ships
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
        Session object
    wait : wait function

    Returns
    -------
    ships : int
        number of available ships
    """
    while True:
        available_ships = getAvailableShips(session)
        if available_ships > 0:
            return available_ships
        minimum_waiting_time_for_ship = getMinimumWaitingTime(session)
        wait(minimum_waiting_time_for_ship, 'Waiting some ships to get available')
