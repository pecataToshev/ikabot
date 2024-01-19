import logging
import re
import sys
import traceback

from ikabot import config
from ikabot.command_line import menu
from ikabot.helpers.database import Database
from ikabot.helpers.logs import setup_logging
from ikabot.helpers.userInput import read
from ikabot.helpers.telegram import Telegram
from ikabot.migrations.migrate import apply_migrations
from ikabot.web.ikariamService import IkariamService


def main():
    named_params, config.predetermined_input = __init_parameters()
    apply_migrations()
    setup_logging(named_params)

    config.BOT_NAME = read(msg='Please provide the unique bot identifier for this account: ')

    db = Database(config.BOT_NAME)
    telegram = Telegram(db, True)

    ikariam_service = IkariamService(db, telegram)
    try:
        menu(ikariam_service, db, telegram)
    except Exception:
        logging.error("Error when trying to close the main function\n%s", traceback.format_exc())
    finally:
        ikariam_service.logout()
        db.close_db_conn()


def __init_parameters():
    named_params = {}
    positional_params = []

    for element in sys.argv:
        match = re.match(r'--(\w+)=(\w+)', element)
        if match:
            key, value = match.groups()
            named_params[key] = value
            continue

        try:
            positional_params.append(int(element))
        except ValueError:
            positional_params.append(element)

    positional_params.pop(0)  # Remove the script path
    return named_params, positional_params


if __name__ == '__main__':
    main()
