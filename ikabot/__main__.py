import multiprocessing
import sys

from ikabot.command_line import start_command_line
from ikabot.migrations.migrate import apply_migrations


def main():
    apply_migrations()
    start_command_line()


if __name__ == '__main__':
    # On Windows calling this function is necessary.
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()

    main()
