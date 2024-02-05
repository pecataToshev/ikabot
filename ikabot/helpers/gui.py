#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
import os
import re
import time
from datetime import datetime
from decimal import Decimal

from ikabot import __version__, config
from ikabot.config import isWindows


def enter():
    """Wait for the user to press Enter
    """
    try:
        if len(config.predetermined_input) > 0:
            return
    except Exception:
        pass
    if isWindows:
        input('\n[Enter]')  # TODO improve this
    else:
        getpass.getpass('\n[Enter]')


def clear():
    """Clears all text on the console
    """
    if isWindows:
        os.system('cls')
    else:
        os.system('clear')


def banner():
    """Clears all text on the console and displays the Ikabot ASCII art banner
    """
    clear()
    bner = """
    `7MMF'  `7MM                       `7MM\"""Yp,                 mm
      MM      MM                         MM    Yb                 MM
      MM      MM  ,MP'   ,6"Yb.          MM    dP    ,pW"Wq.    mmMMmm
      MM      MM ;Y     8)   MM          MM\"""bg.   6W'   `Wb     MM
      MM      MM;Mm      ,pm9MM          MM    `Y   8M     M8     MM
      MM      MM `Mb.   8M   MM          MM    ,9   YA.   ,A9     MM
    .JMML.  .JMML. YA.  `Moo9^Yo.      .JMMmmmd9     `Ybmd9'      `Mbmo
    """
    print('\n{}\nversion {}\n\n{}\n{}'.format(bner, __version__, config.infoUser, config.update_msg))


def printProgressBar(msg, current, total):
    """
    Prints progress bar in format: {msg}: [####=...] 5/8
    :param msg: str
    :param current: int -> current loading
    :param total: int -> total things to load
    :return: void
    """
    banner()
    loaded = "#" * (current - 1)
    waiting = "." * (total - current)
    print("{}: [{}={}] {}/{}".format(msg, loaded, waiting, current, total))


def rightAlign(data, length):
    """
    Right align the given data with the given length
    :param data:
    :param length: int
    :return: str
    """
    return "{:>{len}}".format(data, len=length)


def printTable(table_config, table_data, missing_value='', column_align='>',
               row_additional_indentation='', row_color=lambda i: bcolors.ENDC):
    """
    Formats table and prints it

    possible column specification:
    {
        'key': str -> how to get the value from the data dict[]
        'title': str -> title of the column in the printed table
        'fmt': None/lambda -> if the value has to be transformed before print
        'align': char -> align character of the column values
        'setColor': None/lambda -> set color to the cell (uses value before transformation)
    }

    :param table_config: list[dict[]] -> table columns config
    :param table_data: list[dict[]] -> data to print
    :param missing_value: str -> what to print if value is missing
    :param column_align: str -> default align of all table columns
    :param row_additional_indentation: str -> add some prefix data before
                                              printing the row
    :param row_color: lambda int -> str: determine row color by row index
                                        starting with 0 for table headers
    :return: void
    """
    print()
    if len(table_data) == 0:
        return

    _max_len = [len(tc['title']) for tc in table_config]
    _table = [[{'data': tc['title'], 'color': ''} for tc in table_config]]
    for row_index, row_data in enumerate(table_data):
        _row = []
        for column_index, column_config in enumerate(table_config):
            _raw_column_data = row_data.get(column_config['key'], None)
            _v = _raw_column_data
            if 'fmt' in column_config and _v is not None:
                _v = column_config['fmt'](_v)
            if 'useDataRowIndexForValue' in column_config:
                _v = column_config['useDataRowIndexForValue'](row_index)
            _v = str(_v or missing_value)
            _max_len[column_index] = max(_max_len[column_index], len(_v))
            _color = ''
            if 'setColor' in column_config:
                _color = column_config['setColor'](_raw_column_data)
            _row.append({'data': _v, 'color': _color})
        _table.append(_row)

    for tri, tr in enumerate(_table):
        row_clr = row_color(tri)
        print(row_clr + row_additional_indentation + (row_clr + ' | ').join(
            ['{color}{data: {align}{len}}'.format(
                align=table_config[ci].get('align', column_align),
                len=_max_len[ci],
                **c,
            )
             for ci, c in enumerate(tr)]
        ) + bcolors.ENDC)

    print()


def addThousandSeparator(num, character='.', include_sign=False):
    """Formats the number into a string and adds a `character` for every thousand (eg. 3000 -> 3.000)
    Parameters
    ----------
    num : int
        integer number to format
    character : str
        character to act as the thousand separator
    include_sign : bool
        Show + infront of the number
    Returns
    -------
    number : str
        a string representing that number with added `character` for every thousand
    """
    sign = '+' if include_sign else ''
    return format(int(num), sign+',').replace(',', character)


def daysHoursMinutes(total_seconds):
    """Formats the total number of seconds into days hours minutes (eg. 321454 -> 3D 17H)
    Parameters
    ----------
    total_seconds : int
        total number of seconds

    Returns
    -------
    text : str
        formatted string (D H M S)
    """
    total_seconds = int(total_seconds)
    if total_seconds == 0:
        return '0S'
    days = int(total_seconds / Decimal(86400))
    total_seconds -= days * Decimal(86400)
    hours = int(total_seconds / Decimal(3600))
    total_seconds -= hours * Decimal(3600)
    minutes = int(total_seconds / Decimal(60))
    seconds = int(total_seconds % 60)
    texto = ''
    if days > 0:
        texto = str(days) + 'D '
    if hours > 0:
        texto = texto + str(hours) + 'H '
    if days == 0 and minutes > 0:
        texto = texto + str(minutes) + 'M '
    if days == 0 and hours == 0 and seconds > 0:
        texto = texto + str(seconds) + 'S '
    return texto[:-1]


def getDateTime(timestamp = None):
    """Returns a string of the current date and time in the YYYY-mm-dd_HH-MM-SS, if `timestamp` is provided then it converts it into the given format.
    Parameters
    ----------
    timestamp : int
        Unix timestamp to be converted

    Returns
    -------
    text : str
        Formatted string YYYY-mm-dd_HH-MM-SS
    """
    timestamp = timestamp if timestamp else time.time()
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H-%M-%S')

def decodeUnicodeEscape(input_string):
    """
    Replace Unicode escape sequences (e.g., u043c) with corresponding UTF-8 characters.

    Parameters:
    - input_string (str): The original string.

    Returns:
    - str: The string with replaced Unicode escape sequences.
    """
    return re.sub(r'u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), input_string)


def formatTimestamp(seconds):
    """
    Makes time readable.
    :param seconds: int
    :return:
    """
    return datetime.fromtimestamp(seconds).strftime('%b %d %H:%M:%S')


class bcolors:
    HEADER = '\033[95m'
    STONE = '\033[37m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    BLACK = '\033[90m'
    ENDC = '\033[0m'
    WOOD = '\033[0;33m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DARK_RED = '\033[31m'
    DARK_BLUE = '\033[34m'
    DARK_GREEN = '\033[32m'
