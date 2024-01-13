import logging
import traceback
from abc import ABC, abstractmethod

from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal


class Bot(ABC):
    @abstractmethod
    def _get_process_info(self) -> str:
        raise NotImplementedError('Implement me in the current bot class')

    @abstractmethod
    def _start(self) -> None:
        raise NotImplementedError('Implement me in the current bot class')

    def __init__(self, session, bot_config):
        logging.info("Hi from Bot")
        self.session = session
        self.bot_config = bot_config

    def start(self):
        logging.info("Hi From Start")
        set_child_mode(self.session)
        logging.info("Starting %s with config: %s", self.__class__.__name__, self.bot_config)
        setInfoSignal(self.session, self._get_process_info())

        try:
            self._start()

        except Exception:
            msg = 'Error in:\n{}\nCause:\n{}'.format(self._get_process_info(), traceback.format_exc())
            sendToBot(self.session, msg)
        finally:
            self.session.logout()