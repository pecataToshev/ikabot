#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import time
from datetime import datetime

import psutil

from ikabot.config import isWindows
from ikabot.helpers.gui import formatTimestamp, printTable
from ikabot.helpers.signals import deactivate_sigint


def set_child_mode(session):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    """
    session.padre = False
    deactivate_sigint()


def run(command):
    ret = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
    try:
        return ret.decode('utf-8').strip()
    except Exception:
        return ret


class IkabotProcessListManager:
    __process_list_key = 'processList'

    def __init__(self, session):
        """
        Init processes -> reads and updates the file
        :param session: ikabot.web.session.Session
        """
        self.__session = session

    def __get_processes(self):
        """
        Reads all process from session_data.
        :return: dict[dict[]] -> dict of processes
        """
        process_list = self.__session.db.get_processes()

        # check it's still running
        running_ikabot_processes = []
        ika_process = psutil.Process(pid=os.getpid()).name()
        for process in process_list:
            try:
                proc = psutil.Process(pid=process['pid'])
            except psutil.NoSuchProcess:
                continue

            # windows doesn't support the status method
            is_alive = True if isWindows else proc.status() != 'zombie'

            if is_alive and proc.name() == ika_process:
                running_ikabot_processes.append(process)

        return {p['pid']: p for p in running_ikabot_processes}

    def get_process_list(self, filtering=None):
        """
        Returns processes as list with the applied filter
        :param filtering: lambda x: bool -> filter of the processes to return
        :return: list[dict[]]
        """
        return [p for p in self.__get_processes().values() if filtering is None or filtering(p)]

    def upsert_process(self, process):
        """
        Insert or updates process data.
        :param process: dict[] -> process to update
        :return:
        """
        _processes = self.__get_processes()
        _pid = process.get('pid', os.getpid())

        print("_pid", _pid)
        print("_processes.get(_pid, {})", _processes.get(_pid, {}))
        print("process", process)

        # Merge with old data
        _new_process = dict(_processes.get(_pid, {}))
        _new_process.update(process)
        _new_process['date'] = time.time()
        _new_process['pid'] = _pid

        # Save
        self.__session.db.set_process(_new_process)

        # Print process
        _log_process = dict(_new_process)
        _log_process.pop('pid')
        _log_process.pop('date')
        if _log_process.get('nextActionDate', None) is not None:
            _log_process['nextActionDate'] = formatTimestamp(_log_process['nextActionDate'])
        logging.info("Upsert process: %s", _log_process)

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
            return "{} ({})".format(formatTimestamp(t),
                                    datetime.utcfromtimestamp(t - now).strftime('%H:%M:%S'))

        additional_columns = []
        if add_process_numbers:
            additional_columns.append({
                'key': 'no-data',
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
                {'key': 'status', 'title': 'Status'},
                {'key': 'date', 'title': 'Last Action', 'fmt': formatTimestamp},
                {'key': 'nextActionDate', 'title': 'Next Action', 'fmt': __fmt_next_action},
                {'key': 'targetCity', 'title': 'Target City'},
                {'key': 'objective', 'title': 'Objective'},
                {'key': 'info', 'title': 'Info'},
            ],
        )
