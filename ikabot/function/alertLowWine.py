#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import traceback
from decimal import Decimal, getcontext

from ikabot import config
from ikabot.config import city_url, SECONDS_IN_HOUR
from ikabot.helpers.botComm import checkTelegramData, sendToBot
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import banner, daysHoursMinutes, enter
from ikabot.helpers.pedirInfo import getIdsOfCities, read
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.resources import getProductionPerSecond
from ikabot.helpers.signals import setInfoSignal

getcontext().prec = 30


def alertLowWine(session, event, stdin_fd, predetermined_input):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    try:
        if checkTelegramData(session) is False:
            event.set()
            return
        banner()
        hours = read(msg='How many hours should be left until the wine runs out in a city so that it\'s alerted?', min=1, digit=True)
        print('It will be alerted when the wine runs out in less than {:d} hours in any city'.format(hours))
        enter()

    except KeyboardInterrupt:
        event.set()
        return

    session.setProcessObjective(
        action='Monitoring Wine',
        objective='Wine Hours {}'.format(hours)
    )

    set_child_mode(session)
    event.set()

    info = '\nI alert if the wine runs out in less than {:d} hours\n'.format(hours)
    setInfoSignal(session, info)
    try:
        do_it(session, hours)
    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()


def do_it(session, hours):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    hours : int
    """

    was_alerted = {}
    while True:
        session.setProcessInfo('Checking for low wine')

        # getIdsOfCities is called on a loop because the amount of cities may change
        ids, cities = getIdsOfCities(session)

        for cityId in cities:
            if cityId not in was_alerted:
                was_alerted[cityId] = False

        for cityId in cities:
            html = session.get(city_url + cityId)
            city = getCity(html)

            # if the city doesn't even have a tavern built, ignore it
            if 'tavern' not in [building['building'] for building in city['position']]:
                continue

            consumption_per_hour = city['wineConsumptionPerHour']

            # is a wine city
            if cities[cityId]['tradegood'] == '1':
                wine_production = getProductionPerSecond(session, cityId)[1] * SECONDS_IN_HOUR
                if consumption_per_hour > wine_production:
                    consumption_per_hour -= wine_production
                else:
                    was_alerted[cityId] = False
                    continue

            consumption_per_seg = Decimal(consumption_per_hour) / Decimal(SECONDS_IN_HOUR)
            wine_available = city['availableResources'][1]

            if consumption_per_seg == 0:
                if was_alerted[cityId] is False:
                    msg = 'The city {} is not consuming wine!'.format(city['name'])
                    sendToBot(session, msg)
                    was_alerted[cityId] = True
                continue

            seconds_left = Decimal(wine_available) / Decimal(consumption_per_seg)
            if seconds_left < hours*60*60:
                if was_alerted[cityId] is False:
                    time_left = daysHoursMinutes(seconds_left)
                    msg = 'In {}, the wine will run out in {}'.format(time_left, city['name'])
                    sendToBot(session, msg)
                    was_alerted[cityId] = True
            else:
                was_alerted[cityId] = False

        session.wait(20*60, 'I wait for the next check')
