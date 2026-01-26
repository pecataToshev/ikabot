#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import signal
import subprocess
import time
from datetime import datetime
from enum import Enum
from typing import Union

import psutil

from ikabot.config import isWindows
from ikabot.helpers.database import Database
from ikabot.helpers.gui import (Colours, daysHoursMinutes, formatTimestamp,
                                printTable)


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
    PAUSED = 'paused'

    @staticmethod
    def get_colour(status, row):
        if status in [ProcessStatus.ERROR, ProcessStatus.FORCE_KILLED]:
            return Colours.Text.Light.RED
        if status in [ProcessStatus.TERMINATED, ProcessStatus.ZOMBIE]:
            return Colours.Text.Light.YELLOW
        if status in [ProcessStatus.PAUSED]:
            return Colours.Text.Light.CYAN
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
    except (OSError, IOError) as e:
        # Handle cases where /proc is not accessible
        logging.debug('Unable to check process status for pid %s: %s', process.get('pid'), str(e))
        # Assume the process is still running if we can't check
        return None

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
        try:
            ika_process_name = psutil.Process(pid=os.getpid()).name()
        except (OSError, IOError) as e:
            # Handle cases where /proc is not accessible (e.g., in some Docker environments)
            logging.warning('Unable to access process information (likely /proc not mounted): %s. Process management will be limited.', str(e))
            # Fallback: just use 'python' as a generic name
            ika_process_name = 'python'
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

            # Check for paused status (Unix only, Windows doesn't easily show suspended status)
            if not isWindows:
                try:
                    proc = psutil.Process(pid=process['pid'])
                    if proc.status() == 'stopped':
                        process['status'] = ProcessStatus.PAUSED
                except Exception:
                    # In some environments (Docker, restricted VPS), psutil might fail to read process status.
                    # We just ignore it and rely on the DB status set by suspend_process.
                    pass

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
            print_row_separator=lambda i: i == 0
        )

    def suspend_process(self, process):
        """
        Suspends the given process
        """
        logging.info("Suspending process: %s", process)
        try:
            if isWindows:
                proc = psutil.Process(pid=process['pid'])
                proc.suspend()
            else:
                os.kill(process['pid'], signal.SIGSTOP)
            
            # We can update the DB immediately to reflect the change, 
            # though get_processes will also detect it dynamically.
            process['status'] = ProcessStatus.PAUSED
            self.__db.set_process(process)
        except Exception as e:
            logging.error("Failed to suspend process %s: %s", process.get('pid'), str(e))

    def resume_process(self, process):
        """
        Resumes the given process
        """
        logging.info("Resuming process: %s", process)
        try:
            if isWindows:
                proc = psutil.Process(pid=process['pid'])
                proc.resume()
            else:
                os.kill(process['pid'], signal.SIGCONT)

            # We assume it goes back to running, though it might be waiting.
            # Best to let the process itself update the status, or just wait for detection.
            # But we can optimistically set it to RUNNING (or whatever it was before if we knew).
            # For now, let's just not force the DB status back, as the process will continue its execution loop.
            # However, to stop showing "PAUSED" immediately in the UI if we don't refresh:
            # We'll rely on the next refresh to clear the PAUSED status because proc.status() won't be 'stopped'.
            # But let's verify if we should clear the 'paused' from DB if we wrote it there.
            if process['status'] == ProcessStatus.PAUSED:
                 # It was paused. We don't know the previous status. 
                 # Safe guess: RUNNING. It will correct itself quickly.
                 process['status'] = ProcessStatus.RUNNING 
                 self.__db.set_process(process)

        except Exception as e:
            logging.error("Failed to resume process %s: %s", process.get('pid'), str(e))

    def wakeup_process(self, process):
        """
        Wakes up the given process (skips waiting time)
        """
        logging.info("Waking up process: %s", process)
        try:
            if isWindows:
                # Windows doesn't handle SIGUSR1 natively for Python processes nicely without win32api
                # For now, we'll log a warning or use a workaround if needed.
                # Since the user is on Mac, we prioritize that. 
                logging.warning("Wake up (Skip Wait) is not fully supported on Windows yet.")
            else:
                os.kill(process['pid'], signal.SIGUSR1)
        except Exception as e:
            logging.error("Failed to wake up process %s: %s", process.get('pid'), str(e))
