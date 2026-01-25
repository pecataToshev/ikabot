#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.config import isWindows
from ikabot.helpers.database import Database
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.ikabotProcessListManager import IkabotProcessListManager, ProcessStatus, run
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


def manage_tasks(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    process_list_manager = IkabotProcessListManager(db)

    while True:
        banner()

        process_list = process_list_manager.get_process_list()

        if len(process_list) == 0:
            print('There are no tasks running')
            enter()
            return

        print('Select a task to manage:\n')
        print(' 0) Exit')
        process_list_manager.print_proces_table(
            process_list=process_list,
            add_process_numbers=True,
        )
        choice = read(min=0, max=len(process_list), digit=True)
        if choice == 0:
            return

        process = process_list[choice - 1]

        print('\nWhat action do you want to perform on process {pid} ({action})?'.format(**process))
        print(' 0) Back')
        print(' 1) Kill')
        print(' 2) Pause')
        print(' 3) Resume')
        print(' 4) Wake Up / Skip Wait')
        action_choice = read(min=0, max=4, digit=True)

        if action_choice == 0:
            continue

        if action_choice == 1:
            # Kill
            print('Killing process {pid} | {action} | {objective}'.format(**process))
            if isWindows:
                run("taskkill /F /PID {}".format(process['pid']))
            else:
                run("kill -9 {}".format(process['pid']))

            process['status'] = ProcessStatus.FORCE_KILLED
            process['nextActionTime'] = None
            process_list_manager.upsert_process(process)
            print("Process killed.")
            enter()

        elif action_choice == 2:
            # Pause
            if process['status'] == ProcessStatus.PAUSED:
                print("Process is already paused.")
                enter()
                continue
            process_list_manager.suspend_process(process)
            print("Process suspended.")
            enter()

        elif action_choice == 3:
            # Resume
            # We don't strictly check if it's running because it might be 'waiting' but actually suspended in OS
            process_list_manager.resume_process(process)
            print("Process resumed.")
            enter()
        
        elif action_choice == 4:
            # Wake Up
            process_list_manager.wakeup_process(process)
            print("Process woken up (wait skipped).")
            enter()
