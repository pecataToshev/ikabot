#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import time

from ikabot.helpers.naval import get_military_and_see_movements, getAvailableShips


def get_random_wait_time():
    return random.randint(0, 20) * 3


def getMinimumWaitingTime(ikariam_service):
    """This function returns the time needed to wait for the closest fleet to arrive. If all ships are unavailable,
    this represents the minimum time needed to wait for any ships to become available.
    A random waiting time between 0 and 10 seconds is added to the waiting time to avoid race conditions between
    multiple concurrently running processes.
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
        Session object

    Returns
    -------
    timeToWait : int
        the minimum waiting time for the closest fleet to arrive
    """
    military_movements = get_military_and_see_movements(ikariam_service)
    current_time = time.time()
    delivered_times = []
    for military_movement in [mv for mv in military_movements if mv['isOwnArmyOrFleet']]:
        remaining_time = int(military_movement['eventTime']) - current_time
        delivered_times.append(remaining_time)
    if delivered_times:
        return min(delivered_times) + get_random_wait_time()
    else:
        return 0


def waitForAvailableShips(session, wait, additional=''):
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
        wait(minimum_waiting_time_for_ship, 'Waiting some ships to get available' + additional)
