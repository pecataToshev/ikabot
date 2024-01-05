#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import traceback

from ikabot import config
from ikabot.config import actionRequest, city_url
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.gui import banner, enter, getDateTime
from ikabot.helpers.pedirInfo import getIdsOfCities
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal


def loginDaily(session, event, stdin_fd, predetermined_input):
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
        banner()
        print('I will enter every day.')
        enter()
    except KeyboardInterrupt:
        event.set()
        return

    set_child_mode(session)
    event.set()

    info = '\nI enter every day\n'
    setInfoSignal(session, info)
    try:
        do_it(session)
    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()


def do_it(session):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    """
    while True:
        (ids, cities) = getIdsOfCities(session)
        for id in ids:
            html = session.post(city_url + str(id))
            if 'class="fountain' in html:
                url = 'action=AvatarAction&function=giveDailyActivityBonus&dailyActivityBonusCitySelect={0}&startPageShown=1&detectedDevice=1&autoLogin=on&cityId={0}&activeTab=multiTab2&backgroundView=city&currentCityId={0}&actionRequest={1}&ajax=1'.format(id, actionRequest)
                session.post(url)
                if 'class="fountain_active' in html:
                    url = 'action=AmbrosiaFountainActions&function=collect&backgroundView=city&currentCityId={0}&templateView=ambrosiaFountain&actionRequest={1}&ajax=1'.format(id, actionRequest)
                    session.post(url)
                break
        session.wait(24*60*60, max_random=60, info=f'Last login @{getDateTime()}')
