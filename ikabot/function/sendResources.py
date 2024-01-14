#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import traceback

from ikabot import config
from ikabot.config import materials_names
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.gui import addThousandSeparator, banner
from ikabot.helpers.pedirInfo import askForValue, chooseCity, read
from ikabot.helpers.planRoutes import executeRoutes
from ikabot.helpers.ikabotProcessListManager import set_child_mode
from ikabot.helpers.signals import setInfoSignal


def sendResources(session, event, stdin_fd, predetermined_input):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    try:
        routes = []
        while True:

            banner()
            print('Origin city:')
            try:
                cityO = chooseCity(session)
            except KeyboardInterrupt:
                if routes:
                    print('Send shipment? [Y/n]')
                    rta = read(values=['y', 'Y', 'n', 'N', ''])
                    if rta.lower() != 'n':
                        break
                event.set()
                return

            banner()
            print('Destination city')
            cityD = chooseCity(session, foreign=True)
            idIsland = cityD['islandId']

            if cityO['id'] == cityD['id']:
                continue

            resources_left = cityO['availableResources']
            for route in routes:
                (origin_city, destination_city, __, *toSend) = route
                if origin_city['id'] == cityO['id']:
                    for i in range(len(materials_names)):
                        resources_left[i] -= toSend[i]

                # the destination city might be from another player
                if cityD['isOwnCity'] and destination_city['id'] == cityD['id']:
                    for i in range(len(materials_names)):
                        cityD['freeSpaceForResources'][i] -= toSend[i]

            banner()
            # the destination city might be from another player
            if cityD['isOwnCity']:
                msg = ''
                for i in range(len(materials_names)):
                    if resources_left[i] > cityD['freeSpaceForResources'][i]:
                        msg += '{} more {}\n'.format(addThousandSeparator(cityD['freeSpaceForResources'][i]), materials_names[i].lower())

                if len(msg) > 0:
                    print('You can store just:\n{}'.format(msg))

            print('Available:')
            for i in range(len(materials_names)):
                print('{}:{} '.format(materials_names[i], addThousandSeparator(resources_left[i])), end='')
            print('')

            print('Send:')
            try:
                max_name = max([len(material) for material in materials_names])
                send = []
                for i in range(len(materials_names)):
                    material_name = materials_names[i]
                    pad = ' ' * (max_name - len(material_name))
                    val = askForValue('{}{}:'.format(pad, material_name), resources_left[i])
                    send.append(val)
            except KeyboardInterrupt:
                continue
            if sum(send) == 0:
                continue

            banner()
            print('About to send from {} to {}'.format(cityO['cityName'], cityD['cityName']))
            for i in range(len(materials_names)):
                if send[i] > 0:
                    print('{}:{} '.format(materials_names[i], addThousandSeparator(send[i])), end='')
            print('')

            print('Proceed? [Y/n]')
            rta = read(values=['y', 'Y', 'n', 'N', ''])
            if rta.lower() != 'n':
                route = (cityO, cityD, idIsland, *send)
                routes.append(route)
                print('Create another shipment? [y/N]')
                rta = read(values=['y', 'Y', 'n', 'N', ''])
                if rta.lower() != 'y':
                    break
    except KeyboardInterrupt:
        event.set()
        return

    set_child_mode(session)
    event.set()

    info = '\nSend resources\n'

    setInfoSignal(session, info)
    try:
        executeRoutes(session, routes)
    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()
