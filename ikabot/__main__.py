import logging
import re
import sys
import traceback
from typing import List

from ikabot import config
from ikabot.command_line import menu
from ikabot.helpers.database import Database
from ikabot.helpers.logs import setup_logging
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import read
from ikabot.migrations.migrate import apply_migrations
from ikabot.web.ikariamService import IkariamService


def main():
    config.application_params, config.predetermined_input = init_parameters(sys.argv)
    config.predetermined_input.pop(0)  # Remove the script path
    setup_logging(config.application_params)

    logging.debug("Named Parameters: %s", config.application_params)
    logging.debug("Arguments: %s", config.predetermined_input)

    config.DB_FILE = config.application_params.get('dbFile', config.DB_FILE)
    print('Using database file: %s' % config.DB_FILE)
    logging.info("Database file: %s", config.DB_FILE)
    apply_migrations()

    config.BOT_NAME = read(msg='Please provide the unique bot identifier for this account: ')
    logging.info('Bot identifier: %s', config.BOT_NAME)

    db = Database(config.BOT_NAME)
    logging.info('Database initialized')
    telegram = Telegram(db, True)
    logging.info('Telegram initialized')

    logging.info('Initializing Ikariam service (this will perform login)...')
    ikariam_service = IkariamService(db, telegram)
    logging.info('Ikariam service initialized successfully')
    
    try:
        logging.info('Starting command menu...')
        menu(ikariam_service, db, telegram)
        logging.info('Menu exited normally')
    except Exception as e:
        logging.error("Error in main function: %s\n%s", str(e), traceback.format_exc())
        print(f'\n⚠️  An error occurred: {str(e)}')
        print('Check the logs for more details.')
    finally:
        logging.info('Cleaning up...')
        ikariam_service.logout()
        db.close_db_conn()
        logging.info('Cleanup complete')


def __parse_param_value(param: str):
    if param.lower() in ('true', 'on'):
        return True
    elif param.lower() in ('false', 'off'):
        return False
    elif param.isdigit():
        return int(param)
    else:
        return param


def init_parameters(input_args: List[str]):
    named_params = {}
    positional_params = []

    pattern = re.compile(r'--(\w+)(?:=(\S+))?')
    for element in input_args:
        match = pattern.match(element)
        if match:
            key, val = match.groups()
            if val is not None:
                named_params[key] = __parse_param_value(val)
            else:
                named_params[key] = True
        else:
            positional_params.append(__parse_param_value(element))

    return named_params, positional_params


if __name__ == '__main__':
    main()
