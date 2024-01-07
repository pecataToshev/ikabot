#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import os
import sys

from ikabot import config
from ikabot.config import isWindows
from ikabot.helpers.gui import banner, enter, formatTimestamp, printTable
from ikabot.helpers.pedirInfo import read
from ikabot.helpers.process import IkabotProcessListManager, run


def killTasks(session, event, stdin_fd, predetermined_input):
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
        process_list_manager = IkabotProcessListManager(session)

        while True:
            banner()

            process_list = process_list_manager.get_process_list()
            other_tasks = [process for process in process_list if process['action'] != 'killTasks']
            if len(other_tasks) == 0:
                print('There are no tasks running')
                enter()
                event.set()
                return

            print('Which task do you wish to kill?\n')
            print(' 0) Exit')
            process_list_manager.print_proces_table(True)
            choice = read(min=0, max=len(process_list), digit=True)
            if choice == 0:
                event.set()
                return

            process_to_kill = process_list[choice - 1]

            if process_to_kill['action'] == 'killTasks':
                print('You cannot kill me.... From here...')
                enter()
                continue

            if isWindows:
                run("taskkill /F /PID {}".format(process_to_kill['pid']))
            else:
                run("kill -9 {}".format(process_to_kill['pid']))
    except KeyboardInterrupt:
        event.set()
        return
