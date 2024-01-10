#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

from ikabot import config
from ikabot.config import isWindows
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.pedirInfo import read
from ikabot.helpers.process import IkabotProcessListManager, run

_zombie = 'zombie'


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

            process_list = process_list_manager.get_process_list(
                filtering=lambda p: p['action'] != 'killTasks'
            )

            if len(process_list) == 0:
                print('There are no tasks running')
                enter()
                event.set()
                return

            print('Which task do you wish to kill?\n')
            print('Write {} to kill all zombie processes'.format(_zombie))
            print(' 0) Exit')
            process_list_manager.print_proces_table(
                process_list=process_list,
                add_process_numbers=True,
            )
            choice = read(min=0, max=len(process_list), digit=True, additionalValues=[_zombie])

            if choice == 0:
                event.set()
                return
            elif choice == _zombie:
                print()
                killed_processes = 0
                for p in process_list:
                    if p.get('status', '') != 'zombie':
                        continue
                    print('Killing process', p['pid'], p)
                    kill_process(p)
                    killed_processes += 1

                print()
                print('Killed {} processes'.format(killed_processes))
                enter()
            else:
                kill_process(process_list[choice - 1])
    except KeyboardInterrupt:
        event.set()
        return


def kill_process(process):
    """
    Kill process
    :param process: dict[] -> process info
    :return: void
    """
    if isWindows:
        run("taskkill /F /PID {}".format(process['pid']))
    else:
        run("kill -9 {}".format(process['pid']))
