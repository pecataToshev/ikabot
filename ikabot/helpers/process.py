#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import subprocess
import time

import psutil

from ikabot.config import *
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
    __process_table = [
        {'key': 'pid', 'title': 'pid'},
        {'key': 'action', 'title': 'Task'},
        {'key': 'status', 'title': 'Status'},
        {'key': 'date', 'title': 'Last Action Time', 'fmt': lambda x: datetime.datetime.fromtimestamp(x).strftime('%b %d %H:%M:%S')},
        {'key': 'nextActionDate', 'title': 'Next Action Time', 'fmt': lambda x: datetime.datetime.fromtimestamp(x).strftime('%b %d %H:%M:%S')},
        {'key': 'info', 'title': 'Info'},
    ]

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

            logging.info("Update process data %s", str(_new_process))

            # Write to session
            _processes[_pid] = _new_process
            self.__update_processes(_session_data, _processes)

    def print_proces_table(self):
        process_list = self.get_process_list()
        print()
        if len(process_list) == 0:
            return

        _max_len = [len(pt['title']) for pt in self.__process_table]
        _table = [[pt['title'] for pt in self.__process_table]]
        for p in process_list:
            _row = []
            for ind, pt in enumerate(self.__process_table):
                _v = p.get(pt['key'], None)
                if 'fmt' in pt and _v is not None:
                    _v = pt['fmt'](_v)
                _row.append(_v or '-')
                _max_len[ind] = max(_max_len[ind], len(str(_v or '-')))
            _table.append(_row)

        for tr in _table:
            print(' | '.join(
                ['{: ^{len}}'.format(c, len=_max_len[i])
                 for i, c in enumerate(tr)]
            ))

        print()
