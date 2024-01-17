import multiprocessing
import sys

from ikabot import config
from ikabot.command_line import menu
from ikabot.helpers.database import Database
from ikabot.helpers.gui import clear
from ikabot.helpers.logs import setup_logging
from ikabot.helpers.userInput import read
from ikabot.helpers.telegram import Telegram
from ikabot.migrations.migrate import apply_migrations
from ikabot.web.ikariamService import IkariamService


def main():
    apply_migrations()
    setup_logging()

    manager = multiprocessing.Manager()
    config.predetermined_input = manager.list()
    __init_parameters()

    config.BOT_NAME = read(msg='Please provide the unique bot identifier for this account: ')

    db = Database(config.BOT_NAME)
    telegram = Telegram(db, True)

    ikariam_service = IkariamService(db, telegram)
    try:
        menu(ikariam_service, db, telegram)
    finally:
        clear()
        ikariam_service.logout()


def __init_parameters():
    config.has_params = len(sys.argv) > 1
    for arg in sys.argv:
        try:
            config.predetermined_input.append(int(arg))
        except ValueError:
            config.predetermined_input.append(arg)
    config.predetermined_input.pop(0)


if __name__ == '__main__':
    # On Windows calling this function is necessary.
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()

    main()
