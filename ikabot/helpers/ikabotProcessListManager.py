#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import time
from datetime import datetime
from enum import Enum
from typing import Union

import psutil

from ikabot.config import isWindows
from ikabot.helpers.database import Database
from ikabot.helpers.gui import Colours, daysHoursMinutes, formatTimestamp, printTable


def run(command):
    ret = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
    try:
        return ret.decode('utf-8').strip()
    except Exception:
        return ret


class ProcessStatus:
    INITIALIZED = 'initialized'
    DONE = 'done'
    TERMINATED = 'terminated'
    FORCE_KILLED = 'force-killed'
    RUNNING = 'running'
    WAITING = 'waiting'
    ZOMBIE = 'zombie'
    ERROR = 'error'

    @staticmethod
    def get_colour(status, row):
        if status in [ProcessStatus.ERROR, ProcessStatus.FORCE_KILLED]:
            return Colours.Text.Light.RED
        if status in [ProcessStatus.TERMINATED, ProcessStatus.ZOMBIE]:
            return Colours.Text.Light.YELLOW
        if status in [ProcessStatus.DONE]:
            return Colours.Text.Light.GREEN
        return Colours.Text.RESET


class _ProcessSpecialAction(Enum):
    SET_DELETION_TIME = 'set-deletion-time'
    SET_TERMINATED_STATUS = 'set-terminated-status'
    HAS_DIFFERENT_NAME = 'has-different-name'
    SET_ZOMBIE = 'set-zombie'
    HAS_EXPIRED_SHOWTIME = 'do-delete'


def _determine_process_special_action(process: dict, ika_process_name: str) -> Union[_ProcessSpecialAction, None]:
    if process['status'] in [
        ProcessStatus.DONE,
        ProcessStatus.ZOMBIE,
        ProcessStatus.TERMINATED,
        ProcessStatus.ERROR,
        ProcessStatus.FORCE_KILLED
    ]:
        next_action_time = process.get('nextActionTime', None)
        if next_action_time is None:
            return _ProcessSpecialAction.SET_DELETION_TIME
        if time.time() >= next_action_time:
            return _ProcessSpecialAction.HAS_EXPIRED_SHOWTIME
        return None

    try:
        proc = psutil.Process(pid=process['pid'])

        # check if the process is not zombie
        # windows doesn't support the status method
        if isWindows or proc.status() != 'zombie':
            if proc.name() != ika_process_name:
                # not the same name, so probably restarted the system
                return _ProcessSpecialAction.HAS_DIFFERENT_NAME
        else:
            # the process is zombie
            if process['status'] != ProcessStatus.ZOMBIE:
                return _ProcessSpecialAction.SET_ZOMBIE

    except psutil.NoSuchProcess:
        return _ProcessSpecialAction.SET_TERMINATED_STATUS

    return None


class IkabotProcessListManager:
    def __init__(self, db: Database):
        """
        Init processes -> reads and updates the file
        :param db: ikabot.helpers.database.Database
        """
        self.__db = db

    def __get_processes(self, filters=None):
        """
        Reads all process from database.
        :param filters: list[column, relation, value]
        :return: list[dict[]] -> list of processes
        """
        process_list = self.__db.get_processes(filters)

        # check it's still running
        running_ikabot_processes = []
        ika_process_name = psutil.Process(pid=os.getpid()).name()
        deletion_time = time.time() + 30
        for process in process_list:
            action = _determine_process_special_action(process, ika_process_name)

            if action in [_ProcessSpecialAction.HAS_DIFFERENT_NAME, _ProcessSpecialAction.HAS_EXPIRED_SHOWTIME]:
                logging.info('Deleting process: reason=%s, process=%s', action.value, process)
                self.__db.delete_process(process['pid'])
                continue
            elif action == _ProcessSpecialAction.SET_TERMINATED_STATUS:
                logging.info('Process has been terminated or quit unexpectedly: %s', process)
                process['status'] = ProcessStatus.TERMINATED
                process['nextActionTime'] = deletion_time
                self.__db.set_process(process)
            elif action == _ProcessSpecialAction.SET_ZOMBIE:
                logging.info('Found process zombie. Setting to zombie %s', process)
                process['status'] = ProcessStatus.ZOMBIE
                self.__db.set_process(process)
            elif action == _ProcessSpecialAction.SET_DELETION_TIME:
                logging.info('Setting deletion time for process: %s', process)
                process['nextActionTime'] = deletion_time
                self.__db.set_process(process)

            running_ikabot_processes.append(process)

        return running_ikabot_processes

    def get_process_list(self, filters=None):
        """
        Returns processes as list with the applied filter
        :param filters: list[column, relation, value]
        :return: list[dict[]]
        """
        return self.__get_processes(filters)

    def upsert_process(self, process):
        """
        Insert or updates process data.
        :param process: dict[] -> process to update
        :return:
        """
        _pid = process.get('pid', os.getpid())

        _stored_process = self.__get_processes(filters=[['pid', '==', _pid]])
        if len(_stored_process) > 0:
            _stored_process = _stored_process[0]
        else:
            _stored_process = {
                'pid': _pid
            }

        # Merge with old data
        _stored_process.update(process)
        _stored_process['lastActionTime'] = time.time()

        # Save
        self.__db.set_process(_stored_process)

        # Print process
        logging.info(
            "updateProcess: %s | %s | %s | next: %s | obj: %s | city: %s | %s",
            _stored_process.get('pid', '-'),
            _stored_process.get('action', '-'),
            _stored_process.get('status', '-'),
            '-' if _stored_process.get('nextActionTime', None) is None else formatTimestamp(
                _stored_process['nextActionTime']),
            _stored_process.get('objective', '-'),
            _stored_process.get('targetCity', '-'),
            _stored_process.get('info', '-'),
        )

    def print_proces_table(self, process_list=None, add_process_numbers=False):
        """
        Prints process list table
        :param process_list: None/list[dict[]] -> if specified, will format this process list
        :param add_process_numbers: bool -> should I add a numbering of the rows of the table
        :return: void
        """
        now = time.time()

        if process_list is None:
            process_list = self.get_process_list()

        def __fmt_next_action(t):
            remaining_time = int(t - now)
            color = Colours.Text.Light.YELLOW if remaining_time < 120 else ''
            return "{} {}({:>7})".format(formatTimestamp(t),
                                         color,
                                         daysHoursMinutes(remaining_time, add_leading_zeroes_on_smaller_unit=True))

        additional_columns = []
        if add_process_numbers:
            additional_columns.append({
                'title': '#',
                'useDataRowIndexForValue': lambda data_index: "{})".format(data_index + 1)
            })

        printTable(
            table_data=process_list,
            missing_value='-',
            column_align='<',
            table_config=additional_columns + [
                {'key': 'pid', 'title': 'pid'},
                {'key': 'action', 'title': 'Action'},
                {'key': 'status', 'title': 'Status', 'setColour': ProcessStatus.get_colour},
                {'key': 'lastActionTime', 'title': 'Last Action', 'fmt': formatTimestamp},
                {'key': 'nextActionTime', 'title': 'Next Action', 'fmt': __fmt_next_action},
                {'key': 'targetCity', 'title': 'Target City'},
                {'key': 'objective', 'title': 'Objective'},
                {'key': 'info', 'title': 'Info'},
            ],
        )
