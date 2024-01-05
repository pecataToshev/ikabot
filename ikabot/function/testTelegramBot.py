#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from ikabot import config
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.gui import enter
from ikabot.helpers.pedirInfo import read


def testTelegramBot(session, event, stdin_fd, predetermined_input):
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
    try :
        input = read(msg='Enter the massage you wish to see: ')
        msg = "Test message: {}".format(input)
        sendToBot(session, msg)
        enter()
        event.set()
    except KeyboardInterrupt:
        event.set()