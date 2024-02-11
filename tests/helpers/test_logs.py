import datetime
import logging
import os
import time

from ikabot import config
from ikabot.helpers.gui import Colours
from ikabot.helpers.logs import setup_logging

# Manually test to ensure that we've rotated the log file correctly with data from all processes
if __name__ == '__main__':
    setup_logging({
        'logFile': 'logs/test.log',
        'logRotation': 'S'
    })

    p = 0
    for p in range(8):
        pid = os.fork()
        if pid != 0:
            break

    p = p + 1
    config.BOT_NAME = 'process={}'.format(p)

    if p == 1:
        time.sleep(14)

    for i in range(30000):
        if i % 1000 == 0 and i % p == 0:
            print('process %d; iteration %d', p, i)
        logging.info('process %d; iteration %d', p, i)

    print(Colours.Text.Light.GREEN + config.BOT_NAME + ' FINISHED ' + str(datetime.datetime.utcnow()) + Colours.Text.RESET)
