import logging
import os
import random
import time
import traceback
from abc import ABC, abstractmethod

from ikabot import config
from ikabot.helpers.database import Database
from ikabot.helpers.ikabotProcessListManager import IkabotProcessListManager, ProcessStatus
from ikabot.helpers.telegram import Telegram


class Bot(ABC):
    @abstractmethod
    def _get_process_info(self) -> str:
        raise NotImplementedError('Implement me in the current bot class')

    @abstractmethod
    def _start(self) -> None:
        raise NotImplementedError('Implement me in the current bot class')

    def __init__(self, ikariam_service, bot_config):
        self.ikariam_service = ikariam_service
        self.bot_config = bot_config

    def __prepare_and_start_process(self, process_info):
        try:
            logging.info("Preparing %s with config: %s", self.__class__.__name__, self.bot_config)
            self.ikariam_service.padre = False

            # Reinitialize connections
            self.db = Database(bot_name=config.BOT_NAME)
            self.telegram = Telegram(db=self.db, is_user_attached=False)
            self.__process_manager = IkabotProcessListManager(self.db)
            self.ikariam_service.reset_db_telegram(db=self.db, telegram=self.telegram)

            # Insert process into the process table
            self.__process_manager.upsert_process(process_info)

            logging.info("Starting %s with config: %s", self.__class__.__name__, self.bot_config)
            self._start()

            logging.info("Done executing %s with config: %s", self.__class__.__name__, self.bot_config)
            self.__process_manager.upsert_process({
                'status': ProcessStatus.DONE,
                'nextActionTime': None,
            })

        except Exception as e:
            msg = 'Error in: {}\nMessage: {}\nCause: {}'.format(
                self._get_process_info(), str(e), traceback.format_exc()
            )
            self.telegram.send_message(msg)
            self.__process_manager.upsert_process({
                'status': ProcessStatus.ERROR,
                'nextActionTime': None,
            })

        finally:
            self.ikariam_service.logout()
            self.db.close_db_conn()

    def start(self, action, objective, target_city=None):
        """
        Starts bot process and sets action, objective and target_city
        :param action: str -> what the process is doing
        :param objective: str -> what's the end goal of the process
        :param target_city: str/None -> what is the action's beneficent
        :return: int -> pid of the new process
        """
        info_process = {
            'action': action,
            'objective': objective,
            'targetCity': target_city,
            'status': ProcessStatus.INITIALIZED
        }

        logging.info("Forking proces with info: %s", info_process)
        child_pid = os.fork()
        if child_pid != 0:
            return child_pid

        self.__prepare_and_start_process(info_process)
        return os.getpid()

    def _wait(self, seconds, info, max_random=0):
        """
        This function will wait the provided number of seconds plus a random
        number of seconds between min_random and max_random.

        Parameters
        -----------
        seconds : int
            the number of seconds to wait for
        info : str
            Process info for waiting
        max_random : int
            the maximum number of additional seconds to wait for

        Returns
        -----------
        actual_sleep_time : int the time we've actually slept
        """
        if seconds <= 0:
            return

        random_delay = random.randint(0, max_random)
        ratio = (1 + 5 ** 0.5) / 2 - 1  # 0.6180339887498949

        total_sleep_time = seconds + random_delay
        remaining_time = total_sleep_time
        actual_sleep_time = 0

        # The following code adds additional variability to the sleeping time
        while remaining_time > 0:
            actual_sleep_time += remaining_time * ratio
            remaining_time = total_sleep_time - actual_sleep_time

        self.__process_manager.upsert_process({
            'status': 'sleeping',
            'nextActionTime': time.time() + actual_sleep_time,
            'info': info
        })

        time.sleep(actual_sleep_time)

        self.__process_manager.upsert_process({
            'status': 'running',
            'nextActionTime': None,
            'info': 'After ' + info
        })

        return actual_sleep_time

    def _set_process_info(self, message, target_city=None):
        """
        This function will modify the current task info message that
        appears in the table on the main menu

        Parameters
        ----------
        message : Message to be displayed in the table in main menu
        target_city: str/None if there is a change in the target city
        """
        status_update = {
            'info': message,
            'nextAction': None
        }
        if target_city is not None:
            status_update['targetCity'] = target_city
        self.__process_manager.upsert_process(status_update)
