#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import signal

from ikabot.helpers.botComm import sendToBot


def do_nothing(signal, frame):
    pass


def deactivate_sigint():
    signal.signal(signal.SIGINT, do_nothing)



def setInfoSignal(session, info):  # send process info to bot
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    info : str
    """
    info = 'information of the process {}:\n{}'.format(os.getpid(), info)

    def _sendInfo(signum, frame):
        sendToBot(session, info)
    signal.signal(signal.SIGABRT, _sendInfo)  # kill -SIGUSR1 pid, SIGUSR1 replaced with SIGABRT for compatibility
