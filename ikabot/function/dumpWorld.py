#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import gzip
import json
import os

from ikabot.bot.dumpWorldBot import DumpWorldBot
from ikabot.config import isWindows
from ikabot.helpers.database import Database
from ikabot.helpers.gui import banner, Colours, enter, getDateTime
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService

LINE_UP = '\033[1A'
LINE_CLEAR = '\x1b[2K'
#              status, history, start_time
home = 'USERPROFILE' if isWindows else 'HOME'


def dump_world_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()
    print('{}⚠️ BEWARE - THE RESULTING DUMP CONTAINS ACCOUNT IDENTIFYING INFORMATION ⚠️{}\n'.format(Colours.Text.YELLOW, Colours.Text.RESET))
    if not askUserYesNo('This action will take a couple of hours to complete. Are you sure you want to initiate a data dump now'):
        return

    print('Type in the waiting time between each request in miliseconds (default = 1500): ')
    choice = read(min=0, max=10000, digit=True, default=1500)
    waiting_time = int(choice)/1000

    print('Start scan form island id (0 to start from beginning) (default = 0): ')
    choice = read(min=0, digit=True, default=0)
    start_id = int(choice)

    shallow = askUserYesNo('Do you want only shallow data about the islands? If yes you will not be able to search '
                           'the dump by player names but the dump will be quick.')

    dump_path = os.getenv(home) + '/ikabot_world_dumps/s' + str(ikariam_service.server_number) + '-' + str(ikariam_service.server) + '/'
    dump_path = dump_path.replace('\\','/')
    dump_path += getDateTime() + ('_shallow' if shallow else '') + '.json.gz'

    DumpWorldBot(
        ikariam_service=ikariam_service,
        bot_config={
            'shallow': shallow,
            'start_id': start_id,
            'waiting_time': waiting_time,
            'dump_path': dump_path,
        }
    ).start(
        action='Dump world',
        objective='Shallow' if shallow else 'Full',
    )


def view_dump(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    if not os.path.exists(os.getenv(home) + '/ikabot_world_dumps'):
        print('No existing dumps found. Exiting')
        enter()
        return

    files = [file.replace('\\','/') for file in get_files(os.getenv(home) + '/ikabot_world_dumps') if '.json.gz' in file ]

    print('All dumps are stored in ' + os.getenv(home) + '/ikabot_world_dumps\n')
    print('Choose a dump to view:')
    for i, file in enumerate(files):
        print(str(i) + ') ' + file.split('/')[-2] + ' ' + file.split('/')[-1].replace('.json.gz','').replace('_',' '))
    choice = read(min = 0, max = len(files)-1, digit=True)
    print('Loading dump...')
    selected_dump = files[choice]
    with gzip.open(selected_dump, 'rb') as file:
        selected_dump = json.load(file)

    selected_islands = set()
    while True:
        banner()
        print_map(selected_dump['islands'], selected_islands)
        print('0) Back')
        print('1) Search islands by island criteria')
        if not selected_dump['shallow']:
            print('2) Search islands by player name')
            print('3) Search for nearest inactive players')

        choice = read(min=0, max=3, digit=True)
        if choice == 0:
            return
        elif choice == 1:
            print('Search island by a certain criteria. The available properties of an island are:')
            print('resource_type : [1,2,3,4] // these are  Wine, Marble, Cristal, Sulfur')
            print('miracle_type : [1,2,3,4,5,6,7,8] // hephaistos forge is number 5')
            print('wood_lvl : [1..] // this is the forest level on the island')
            print('players : [0..] // number of players on the island')
            print('ex. If I wanted to find all islands with less than 10 players and forest level 30 with hephaistos I would type in:')
            print('players < 10 and wood_lvl == 30 and miracle_type == 5\n')
            condition = read(msg="Enter the condition: ")

            try:
                filtered_islands = [island for island in filter(lambda x: filter_on_condition(x, condition), selected_dump['islands'] if selected_dump['shallow'] else convert_to_shallow(selected_dump['islands']))]
            except (SyntaxError, KeyError):
                print('Condition is bad, please use only the available island properties and use python standard conditional sytnax (and, or, <, >, ==, (, ), etc... )')
                enter()
                continue
            
            print('The satisfying islands are:')
            [print(island) for island in filtered_islands]
            enter()
        elif choice == 2:
            if selected_dump['shallow']:
                print('You can not search by player name because this dump is shallow and doesn\'t contain data about players!')
                enter()
                continue
            player_name = read(msg='Type in the player name: ')
            # search for players by name
            players = []
            for island in selected_dump['islands']:
                for city in island['cities']:
                    if city['type'] != 'empty' and player_name in city['ownerName']:
                        players.append((player_name, island['id']))
            # return if none are found
            if not len(players):
                print('No players found!')
                enter()
                continue
            # select one 
            print('Chose a player to add to selection: ')
            for i, player in enumerate(unique_tuples(players)):
                print(str(i) + ') ' + player[0])
            choice = read(min=0, max=len(list(unique_tuples(players)))-1, digit=True)
            # add his islands to selection
            for player in players:
                if player[0] == list(unique_tuples(players))[choice][0]:
                    selected_islands.add(int(player[1]))
        elif choice == 3:
            if selected_dump['shallow']:
                print('You can not search by player name because this dump is shallow and doesn\'t contain data about players!')
                enter()
                continue
            coords = read(msg='Type in a center point (x,y): ').replace('(','').replace(')','').split(',')
            coords = (int(coords[0]), int(coords[1]))
            number_of_inactives = read(msg='How many inactives should be displayed? (min=1, default=25): ', min = 1, digit=True, default=25)
            #sort islands based on distance from center point
            islands_sorted = sorted(selected_dump['islands'], key=lambda island: ((island['x'] - coords[0]) ** 2 + (island['y'] - coords[1]) ** 2) ** 0.5)
            print('The nearest 25 inactive players are: ')
            #below follows the unholiest way to get the first n cities which are contained in an island object which is contained in a list of islands without duplicates in one line of code using python list comprehension
            seen = set()
            inactives = [city for island in islands_sorted for city in island['cities'] if city['type'] != 'empty' and city['state'] == 'inactive' and isinstance([(seen.add(city['ownerName']),) if city['ownerName'] not in seen else None][0],tuple)][:number_of_inactives]
            for i, city in enumerate(inactives):
                print(str(i+1) + ') ' + city['ownerName'])
            enter()


def print_map(islands, selected_islands):
    """Prints out a 100x100 matrix with all world islands on it. Selected islands are coloured red.
    Parameters
    ----------
    islands : [object]
        List of island objects to be displayed
    """

    map = [[Colours.Text.BLUE + '██' + Colours.Text.RESET for j in range(100)] for i in range(100)] # 100x100 matrix of dark blue ██
    selected_island_coords = []

    for island in islands:
        if int(island['id']) in selected_islands:
            map[int(island['x'])-1][int(island['y'])-1] = Colours.Text.RED + '◉ ' + Colours.Text.RESET 
            selected_island_coords.append((int(island['x']),int(island['y'])))
        else:
            map[int(island['x'])-1][int(island['y'])-1] = Colours.Text.GREEN + '◉ ' + Colours.Text.RESET

    for row in reversed(map):
        print(''.join(row))

    print(Colours.Text.BLUE + '██' + Colours.Text.RESET + ' - Water, ' + \
          Colours.Text.GREEN + '◉' + Colours.Text.RESET + ' - Island, '+ \
          Colours.Text.RED + '◉' + Colours.Text.RESET + ' - Selected\n'
        )

    print('Selected islands: ' + str(selected_island_coords))
    

def filter_on_condition(island, condition):
    """Returns true if island satisfies condition
    Parameters
    ----------
    island : object
        Island to be tested on condition
    condition : str
        String that represents a valid python condition to be applied to filter the list of islands

    Returns
    -------
    is_satisfied : bool
        Bool indicating whether or not the island object satisfies the condition
    """

    condition = ast.parse(condition)
    for node in ast.walk(condition):
        if isinstance(node, ast.Compare):
            left = node.left.id
            right = node.comparators[0].n if isinstance(node.comparators[0], ast.Num) else node.comparators[0].id
            op = node.ops[0]
            if op.__class__ == ast.Lt:
                if not int(island[left]) < int(right):
                    return False
            elif op.__class__ == ast.Gt:
                if not int(island[left]) > int(right):
                    return False
            elif op.__class__ == ast.Eq:
                if not int(island[left]) == int(right):
                    return False
    return True

    

def convert_to_shallow(islands):
    """Converts a list of islands from a deep dump into a shallow dump version of that list
    Parameters
    ----------
    islands : [object]
        List of island objects to be converted
    
    Returns
    -------
    islands : [object]
        List of objects that represent the stripped-down version of an island 
    """
    return [{'x': str(island['x']), 'y': str(island['y']), 'id': island['id'], 'name': island['name'], 'resource_type': island['tradegood'], 'miracle_type': island['wonder'], 'wood_lvl': island['resourceLevel'], 'players': len([city for city in island['cities'] if city['type'] != 'empty'])} for island in islands]

def unique_tuples(tuples):
    """Iterates over tuples with a unique first element
    """
    seen = {}
    for t in tuples:
        if t[0] not in seen:
            seen[t[0]] = True
            yield t

def get_files(path):
    """
    Returns all full paths to every file in a directory and all it's subdirectories
    Parameters
    ----------
    path : str
        Path to directory
    Returns
    -------
    files : list
    """
    files = []
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            files.append(os.path.join(dirpath, filename))
    return files
