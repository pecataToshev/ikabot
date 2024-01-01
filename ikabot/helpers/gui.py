#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass

from ikabot import config
from ikabot.config import *

t = gettext.translation('gui', localedir, languages=languages, fallback=True)
_ = t.gettext


def enter():
    """Wait for the user to press Enter
    """
    try:
        if config.has_params:
            return
    except Exception:
        pass
    if isWindows:
        input(_('\n[Enter]'))  # TODO improve this
    else:
        getpass.getpass(_('\n[Enter]'))


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
    print('\n{}\n\n{}\n{}'.format(bner, config.infoUser, config.update_msg))

def printChoiceList(list):
    """Prints the list with padded numbers next to each list entry.
    Parameters
    ----------
    list : list
        list to be printed
    """
    [print('{:>{pad}}) '.format(str(i+1), pad=len(str(len(list)))) + str(item)) for i, item in enumerate(list)]


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
    for d in table_data:
        _row = []
        for ind, pt in enumerate(table_config):
            _v = d.get(pt['key'], None)
            if 'fmt' in pt and _v is not None:
                _v = pt['fmt'](_v)
            _row.append(_v or missing_value)
            _max_len[ind] = max(_max_len[ind], len(str(_v or missing_value)))
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
