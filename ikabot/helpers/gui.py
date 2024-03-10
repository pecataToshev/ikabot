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
               row_additional_indentation='', row_colour=lambda i, row: Colours.Text.RESET,
               print_row_separator=lambda row_index: False, column_separator=' | '):
    """
    Formats table and prints it

    possible column specification:
    {
        'key': str => how to get the value from the data dict[]
        'title': str => title of the column in the printed table
        'fmt': None/lambda any -> any => if the value has to be transformed before print
        'align': char => align character of the column values
        'setColour': None/lambda any, dict -> str => set colour to the cell (uses value before transformation)
    }

    :param table_config: list[dict[]] -> table columns config
    :param table_data: list[dict[]] -> data to print
    :param missing_value: str -> what to print if value is missing
    :param column_align: str -> default align of all table columns
    :param row_additional_indentation: str -> add some prefix data before
                                              printing the row
    :param row_colour: lambda int, dict -> str: determine row colour by row index
                                               starting with 0 for table headers
    :param print_row_separator: lambda int -> bool: print row separator after printing the row
    :param column_separator: str: separator between table columns
    :return: void
    """
    print()
    if len(table_data) == 0:
        return

    _max_len = [len(tc['title']) for tc in table_config]
    _table = [[{'data': tc['title'], 'colour': ''} for tc in table_config]]
    for row_index, row_data in enumerate(table_data):
        _row = []
        for column_index, column_config in enumerate(table_config):
            _raw_column_data = row_data.get(column_config.get('key', ''), None)
            _v = _raw_column_data
            if 'fmt' in column_config and _v is not None:
                _v = column_config['fmt'](_v)
            if 'useDataRowIndexForValue' in column_config:
                _v = column_config['useDataRowIndexForValue'](row_index)
            _v = str(_v or missing_value)
            _max_len[column_index] = max(_max_len[column_index], len(_v))
            colour = ''
            if 'setColour' in column_config:
                colour = column_config['setColour'](_raw_column_data, row_data)
            _row.append({'data': _v, 'colour': colour})
        _table.append(_row)

    for tri, tr in enumerate(_table):
        row_clr = row_colour(tri, None if tri == 0 else table_data[tri - 1])
        print(row_clr + row_additional_indentation + (row_clr + column_separator).join(
            ['{colour}{data: {align}{len}}'.format(
                align=table_config[ci].get('align', column_align),
                len=_max_len[ci],
                **c,
            )
                for ci, c in enumerate(tr)]
        ) + Colours.Text.RESET)
        if print_row_separator(tri):
            print(row_additional_indentation + '-' * (sum(_max_len) + (len(_max_len) - 1) * len(column_separator)))

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
    return format(int(num), sign + ',').replace(',', character)


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
    res = []

    get_num = lambda x: str(x) if len(res) == 0 else str(x).zfill(2)

    if days > 0:
        res.append(get_num(days) + 'D')
    if hours > 0:
        res.append(get_num(hours) + 'H')
    if days == 0 and minutes > 0:
        res.append(get_num(minutes) + 'M')
    if days == 0 and hours == 0 and seconds > 0:
        res.append(get_num(seconds) + 'S')

    return ' '.join(res)


def getDateTime(timestamp=None):
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


class Colours:
    class Text:
        RESET = '\033[0m'
        BLACK = '\033[0;30m'
        RED = '\033[0;31m'
        GREEN = '\033[0;32m'
        YELLOW = '\033[0;33m'
        BLUE = '\033[0;34m'
        MAGENTA = '\033[0;35m'
        CYAN = '\033[0;36m'
        WHITE = '\033[0;37m'

        class Format:
            BOLD = '\033[1m'
            DIM = '\033[2m'
            UNDERLINED = '\033[4m'
            BLINK = '\033[5m'
            REVERSE = '\033[7m'
            HIDDEN = '\033[8m'

        class Light:
            BLACK = '\033[90m'
            RED = '\033[91m'
            GREEN = '\033[92m'
            YELLOW = '\033[93m'
            BLUE = '\033[94m'
            MAGENTA = '\033[95m'
            CYAN = '\033[96m'
            WHITE = '\033[97m'

    class Background:
        RESET = '\033[49m'
        BLACK = '\033[40m'
        RED = '\033[41m'
        GREEN = '\033[42m'
        YELLOW = '\033[43m'
        BLUE = '\033[44m'
        MAGENTA = '\033[45m'
        CYAN = '\033[46m'
        WHITE = '\033[47m'

        class Light:
            BLACK = '\033[100m'
            RED = '\033[101m'
            GREEN = '\033[102m'
            YELLOW = '\033[103m'
            BLUE = '\033[104m'
            MAGENTA = '\033[105m'
            CYAN = '\033[106m'
            WHITE = '\033[107m'

    MATERIALS = [Text.YELLOW, Text.Light.MAGENTA, Text.Light.WHITE, Text.Light.BLUE, Text.Light.YELLOW]
    SATISFACTION = {
        "ecstatic": Text.GREEN,
        "happy": Text.YELLOW,
        "neutral": Text.WHITE,
        "sad": Text.BLUE,
        "outraged": Text.RED
    }
