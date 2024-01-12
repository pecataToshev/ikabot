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
    def __init__(self, session):
        """
        Init processes -> reads and updates the file
        :param session: ikabot.web.session.Session
        """
        self.__session = session

    def __get_processes(self, filters=None):
        """
        Reads all process from session_data.
        :param filters: list[column, relation, value]
        :return: list[dict[]] -> list of processes
        """
        process_list = self.__session.db.get_processes(filters)

        # check it's still running
        running_ikabot_processes = []
        ika_process = psutil.Process(pid=os.getpid()).name()
        for process in process_list:
            try:
                proc = psutil.Process(pid=process['pid'])
            except psutil.NoSuchProcess:
                # The process is no-longer running
                logging.info('Process is no-longer running. Deleting %s', process)
                self.__session.db.delete_process(process['pid'])
                continue

            # windows doesn't support the status method
            is_alive = True if isWindows else proc.status() != 'zombie'

            if is_alive:
                if proc.name() != ika_process:
                    # not the same name, so probably restarted the system
                    logging.info('Process has different name. Deleting %s', process)
                    self.__session.db.delete_process(process['pid'])
                    continue
            else:
                # the process is zombie
                if process['status'] != 'zombie':
                    logging.info('Found process zombie. Setting to zombie %s', process)
                    process['status'] = 'zombie'
                    self.__session.db.set_process(process)

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
        with self.__session.update_process_list_lock:
            _pid = os.getpid()

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
            self.__session.db.set_process(_stored_process)

            # Print process
            _stored_process.pop('pid')
            _stored_process.pop('lastActionTime')
            if _stored_process.get('nextActionTime', None) is not None:
                _stored_process['nextActionTime'] = formatTimestamp(_stored_process['nextActionTime'])
            logging.info("Upsert process: %s", _stored_process)

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
                {'key': 'lastActionTime', 'title': 'Last Action', 'fmt': formatTimestamp},
                {'key': 'nextActionTime', 'title': 'Next Action', 'fmt': __fmt_next_action},
                {'key': 'targetCity', 'title': 'Target City'},
                {'key': 'objective', 'title': 'Objective'},
                {'key': 'info', 'title': 'Info'},
            ],
        )
