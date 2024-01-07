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
    __process_list = 'processList'

    def __init__(self, session):
        """
        Init processes -> reads and updates the file
        :param session: ikabot.web.session.Session
        """
        self.__session = session

    def __get_processes(self, session_data):
        """
        Reads all process from session_data.
        :param session_data: sessionData
        :return: dict[dict[]] -> dict of processes
        """
        process_list = session_data.get(self.__process_list, [])

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

    def __update_processes(self, session_data, processes):
        """
        Writes processes into session.
        :param session_data: sessionData
        :param processes: dict[dict[]] -> process dict
        :return: None
        """
        session_data[self.__process_list] = [p for p in processes.values()]
        self.__session.setSessionData(session_data)

    def get_process_list(self):
        return self.__get_processes(self.__session.getSessionData()).values()

    def upsert_process(self, process):
        """
        Insert or updates process data.
        :param process: dict[] -> process to update
        :return:
        """
        with self.__session.update_process_list_lock:
            _session_data = self.__session.getSessionData()
            _processes = self.__get_processes(_session_data)
            _pid = process.get('pid', os.getpid())

            # Merge with old data
            _new_process = dict(_processes.get(_pid, {}))
            _new_process.update(process)
            _new_process['date'] = time.time()

            # Print process
            _log_process = dict(_new_process)
            _log_process.pop('pid')
            _log_process.pop('date')
            if _log_process.get('nextActionDate', None) is not None:
                _log_process['nextActionDate'] = formatTimestamp(_log_process['nextActionDate'])
            logging.info("Upsert process: %s", _log_process)

            # Write to session
            _processes[_pid] = _new_process
            self.__update_processes(_session_data, _processes)

    def print_proces_table(self, add_process_numbers=False):
        now = time.time()
        print("now: ", formatTimestamp(now))

        fmt_next_action = lambda t: "{} ({})".format(formatTimestamp(t),
                                                     datetime.utcfromtimestamp(t - now).strftime('%H:%M:%S'))

        additional_columns = []
        if add_process_numbers:
            additional_columns.append({
                'key': 'no-data',
                'title': '#',
                'useDataRowIndexForValue': lambda data_index: "{})".format(data_index + 1)
            })

        printTable(
            table_data=self.get_process_list(),
            missing_value='-',
            column_align='<',
            table_config=additional_columns + [
                {'key': 'pid', 'title': 'pid'},
                {'key': 'action', 'title': 'Action'},
                {'key': 'status', 'title': 'Status'},
                {'key': 'date', 'title': 'Last Action', 'fmt': formatTimestamp},
                {'key': 'nextActionDate', 'title': 'Next Action', 'fmt': fmt_next_action},
                {'key': 'targetCity', 'title': 'Target City'},
                {'key': 'objective', 'title': 'Objective'},
                {'key': 'info', 'title': 'Info'},
            ],
        )
