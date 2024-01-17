#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
import os
import re
import time
from datetime import datetime
from decimal import Decimal

from ikabot import config
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
    # clear() # TODO: remove comment
    bner = """
    `7MMF'  `7MM                       `7MM\"""Yp,                 mm
      MM      MM                         MM    Yb                 MM
      MM      MM  ,MP'   ,6"Yb.          MM    dP    ,pW"Wq.    mmMMmm
      MM      MM ;Y     8)   MM          MM\"""bg.   6W'   `Wb     MM
      MM      MM;Mm      ,pm9MM          MM    `Y   8M     M8     MM
      MM      MM `Mb.   8M   MM          MM    ,9   YA.   ,A9     MM
    .JMML.  .JMML. YA.  `Moo9^Yo.      .JMMmmmd9     `Ybmd9'      `Mbmo
    """
    print('\n{}\n\n{}\n{}'.format(bner, config.infoUser, config.update_msg))


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
    _table = [[tc['title'] for tc in table_config]]
    for row_index, row_data in enumerate(table_data):
        _row = []
        for column_index, column_config in enumerate(table_config):
            _v = row_data.get(column_config['key'], None)
            if 'fmt' in column_config and _v is not None:
                _v = column_config['fmt'](_v)
            if 'useDataRowIndexForValue' in column_config:
                _v = column_config['useDataRowIndexForValue'](row_index)
            _row.append(_v or missing_value)
            _max_len[column_index] = max(_max_len[column_index], len(str(_v or missing_value)))
        _table.append(_row)

    for tri, tr in enumerate(_table):
        print(row_color(tri) + row_additional_indentation + ' | '.join(
            ['{column: {align}{len}}'.format(
                column=c,
                align=table_config[ci].get('align', column_align),
                len=_max_len[ci])
             for ci, c in enumerate(tr)]
        ))

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


def daysHoursMinutes(totalSeconds):
    """Formats the total number of seconds into days hours minutes (eg. 321454 -> 3D 17H)
    Parameters
    ----------
    totalSeconds : int
        total number of seconds

    Returns
    -------
    text : str
        formatted string (D H M S)
    """
    if totalSeconds == 0:
        return '0 s'
    dias = int(totalSeconds / Decimal(86400))
    totalSeconds -= dias * Decimal(86400)
    horas = int(totalSeconds / Decimal(3600))
    totalSeconds -= horas * Decimal(3600)
    minutos = int(totalSeconds / Decimal(60))
    seconds = int(totalSeconds % 60)
    texto = ''
    if dias > 0:
        texto = str(dias) + 'D '
    if horas > 0:
        texto = texto + str(horas) + 'H '
    if minutos > 0 and dias == 0:
        texto = texto + str(minutos) + 'M '
    if dias == 0 and horas == 0 and seconds > 0:
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
