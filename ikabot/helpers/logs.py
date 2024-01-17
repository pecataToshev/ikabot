import logging
import os
from logging.handlers import TimedRotatingFileHandler

from ikabot import config
from ikabot.config import LOG_FILE, LOG_DIR


def __record_factory(old_factory, *args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.botName = ''
    record.customRequestId = ''
    record.customRequest = ''

    if len(config.BOT_NAME) > 0:
        record.botName = '[{}]'.format(config.BOT_NAME)

    return record


def setup_logging(named_params: dict):
    log_level = named_params.get('logLevel', 'Info').upper()
    print('Setup logging:', log_level)
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.getLevelName(log_level),
        datefmt='%Y-%m-%dT%H:%M:%S',
        format='%(asctime)s.%(msecs)03d pid:%(process)-6s %(levelname)-5s %(filename)s %(botName)s - %(message)s',
        handlers=[
            TimedRotatingFileHandler(
                filename=LOG_FILE,
                when='midnight',
            ),
        ]
    )

    __old_factory = logging.getLogRecordFactory()
    logging.setLogRecordFactory(
        lambda *args, **kwargs: __record_factory(__old_factory, *args, **kwargs)
    )
