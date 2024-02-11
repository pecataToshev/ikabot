import fcntl
import glob
import logging
import logging.handlers
import os
import time
from datetime import datetime

from ikabot import config
from ikabot.config import LOG_FILE


class CustomTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    # The purpose of this class is to solve a time-rotating problem we've faced. The issue is that every process
    # is configured to do the file rotation, so when we run multiple instances of the bot, we end up with multiple
    # files rotating at the same time. This class ensures that we only have one process to do the rotation while the
    # rest are still writing to the base file.

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        # We've put the .lock. before the time, because otherwise it was being deleted by the super().doRollover()
        # Yes, this is polluting the folder, but the files are oneliners, and it's not a big deal.
        lock_prefix = self.baseFilename + ".lock."
        lock_file = lock_prefix + time.strftime(self.suffix, time.gmtime(time.time()))
        if not os.path.exists(lock_file):
            with open(lock_file, 'w') as _lockfile:
                try:
                    fcntl.lockf(_lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

                    _lockfile.write(' - '.join([config.BOT_NAME, str(os.getpid()), str(datetime.utcnow())]))

                    super().doRollover()

                    # delete old lock files
                    files = glob.glob(lock_prefix + "*")
                    files.sort(key=os.path.getmtime, reverse=True)
                    for old_file_index in range(self.backupCount, len(files)):
                        os.remove(files[old_file_index])

                except IOError:
                    # we were unable to acquire the lock, so we don't need to do anything
                    pass
                finally:
                    time.sleep(.3)  # just to ensure we have some delay
                    fcntl.lockf(_lockfile, fcntl.LOCK_UN)

        if self.stream is None:
            self.stream = self._open()


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
    log_file = named_params.get('logFile', LOG_FILE)
    log_rotation = named_params.get('logRotation', 'midnight')

    print('Setup logging: level: {}, file: {}, rotation: {}'.format(log_level, log_file, log_rotation))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=logging.getLevelName(log_level),
        datefmt='%Y-%m-%dT%H:%M:%S',
        format='%(asctime)s.%(msecs)03d pid:%(process)-6s %(levelname)-7s %(botName)s - %(message)s',
        handlers=[
            CustomTimedRotatingFileHandler(
                filename=log_file,
                when=log_rotation,
                backupCount=7,
            ),
        ]
    )

    __old_factory = logging.getLogRecordFactory()
    logging.setLogRecordFactory(
        lambda *args, **kwargs: __record_factory(__old_factory, *args, **kwargs)
    )
