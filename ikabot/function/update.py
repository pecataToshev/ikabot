#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from ikabot import config
from ikabot.helpers.gui import enter


def update(session, event, stdin_fd, predetermined_input):
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
        print('To update ikabot run:')
        print('python3 -m pip install --user --upgrade ikabot')
        enter()
        event.set()
    except KeyboardInterrupt:
        event.set()
        return
