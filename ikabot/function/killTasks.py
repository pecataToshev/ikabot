#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.config import isWindows
from ikabot.helpers.database import Database
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.ikabotProcessListManager import IkabotProcessListManager, run
from ikabot.helpers.userInput import read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def kill_tasks(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    process_list_manager = IkabotProcessListManager(db)

    while True:
        banner()

        process_list = process_list_manager.get_process_list(filters=[['action', '!=', 'killTasks']])

        if len(process_list) == 0:
            print('There are no tasks running')
            enter()
            return

        print('Which task do you wish to kill?\n')
        print(' 0) Exit')
        process_list_manager.print_proces_table(
            process_list=process_list,
            add_process_numbers=True,
        )
        choice = read(min=0, max=len(process_list), digit=True)
        if choice == 0:
            return

        process_to_kill = process_list[choice - 1]

        if isWindows:
            run("taskkill /F /PID {}".format(process_to_kill['pid']))
        else:
            run("kill -9 {}".format(process_to_kill['pid']))
