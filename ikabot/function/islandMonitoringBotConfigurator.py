#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.islandMonitoringBot import IslandMonitoringBot
from ikabot.helpers.database import Database
from ikabot.helpers.getJson import getIsland
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def island_monitoring_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    if not telegram.has_valid_data():
        print('Telegram data is required to setup the monitoring. Sorry!')
        enter()
        return

    print('Do you want to search for spaces on your islands or a specific set of islands?')
    print('(0) Exit')
    print('(1) Search all islands I have colonised')
    print('(2) Search a specific set of islands')
    choice = read(min=0, max=2)
    island_ids = []
    if choice == 0:
        return

    elif choice == 1:
        # let them be empty to get them each time we try to scan them
        pass

    elif choice == 2:
        banner()
        print('Insert the coordinates of each island you want searched like so: X1:Y1, X2:Y2, X3:Y3...')
        coords_string = read()
        coords_string = coords_string.replace(' ', '')
        coords = coords_string.split(',')
        for coord in coords:
            coord = '&xcoord=' + coord
            coord = coord.replace(':', '&ycoord=')
            html = ikariam_service.get('view=island' + coord)
            island = getIsland(html)
            island_ids.append(island['id'])

    print('How frequently should the islands be searched in minutes (minimum is 3)?')
    waiting_minutes = int(read(min=3, digit=True))

    print('Do you wish to be notified if on these islands')
    inform_list = []
    for val, msg in [
        [IslandMonitoringBot.inform_fights, 'A fight breaks out or stops'],
        [IslandMonitoringBot.inform_inactive, 'A player becomes active/inactive'],
        [IslandMonitoringBot.inform_vacation, 'A player activates/deactivates vacation'],
    ]:
        if askUserYesNo(' - ' + msg):
            inform_list.append(val)

    IslandMonitoringBot(ikariam_service, {
        'islandsToMonitor': island_ids,
        'waitingMinutes': waiting_minutes,
        'informList': inform_list,
    }).start(
        action='Monitor Islands',
        objective='{} @{}m'.format(
            '/'.join([i.replace('inform-', '') for i in inform_list]),
            waiting_minutes
        )
    )
    print('I will search for changes in the selected islands')
    enter()
