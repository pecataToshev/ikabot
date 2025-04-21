#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import time
from decimal import Decimal

from ikabot.config import materials_names, materials_names_tec
from ikabot.helpers.citiesAndIslands import getCurrentCityId
from ikabot.helpers.gui import (Colours, addThousandSeparator, banner,
                                daysHoursMinutes, enter)
from ikabot.helpers.naval import (TransportShip,
                                  get_military_and_see_movements,
                                  get_transport_ships_size, getAvailableShips,
                                  getTotalShips)


def isHostile(movement):
    """
    Parameters
    ----------
    movement : dict

    Returns
    -------
    is hostile : bool
    """
    if movement['army']['amount']:
        return True
    for mov in movement['fleet']['ships']:
        if mov['cssClass'] != 'ship_transport':
            return True
    return False


def shipMovements(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()

    # TODO: FIX multiple calls to the get
    print('Ships {:d}/{:d}\n'.format(getAvailableShips(ikariam_service), getTotalShips(ikariam_service)))

    movements = get_military_and_see_movements(ikariam_service)
    time_now = int(time.time())

    if len(movements) == 0:
        print('There are no movements')
        enter()
        return

    ship_size = get_transport_ships_size(ikariam_service, getCurrentCityId(ikariam_service), TransportShip.TRANSPORT_SHIP)
    for movement in movements:

        colour = ''
        if movement['isHostile']:
            colour = Colours.Text.Light.RED + Colours.Text.Format.BOLD
        elif movement['isOwnArmyOrFleet']:
            colour = Colours.Text.Light.BLUE + Colours.Text.Format.BOLD
        elif movement['isSameAlliance']:
            colour = Colours.Text.Light.GREEN + Colours.Text.Format.BOLD

        origin = '{} ({})'.format(movement['origin']['name'], movement['origin']['avatarName'])
        destination = '{} ({})'.format(movement['target']['name'], movement['target']['avatarName'])
        arrow = '<-' if movement['event']['isFleetReturning'] else '->'
        time_left = int(movement['eventTime']) - time_now
        print('{}{} {} {}: {} ({}) {}'.format(colour, origin, arrow, destination,
                                              movement['event']['missionText'], daysHoursMinutes(time_left),
                                              Colours.Text.RESET))

        if movement['isHostile']:
            troops = movement['army']['amount']
            fleets = movement['fleet']['amount']
            print('Troops:{}\nFleets:{}'.format(addThousandSeparator(troops), addThousandSeparator(fleets)))
        elif isHostile(movement):
            troops = movement['army']['amount']
            ships = 0
            fleets = 0
            for mov in movement['fleet']['ships']:
                if mov['cssClass'] == 'ship_transport':
                    ships += int(mov['amount'])
                else:
                    fleets += int(mov['amount'])
            print('Troops:{}\nFleets:{}\n Ships:{}'.format(addThousandSeparator(troops), addThousandSeparator(fleets), addThousandSeparator(ships)))
        else:
            assert len(materials_names) == 5
            total_load = 0
            for resource in movement['resources']:
                amount = resource['amount']
                tradegood = resource['cssClass'].split()[1]
                # gold won't be translated
                if tradegood != 'gold':
                    index = materials_names_tec.index(tradegood)
                    tradegood = materials_names[index]
                total_load += int(amount.replace(',', '').replace('.', ''))
                print('{} of {}'.format(amount, tradegood))
            ships = int(math.ceil((Decimal(total_load) / Decimal(ship_size))))
            print('{:d} Ships'.format(ships))

    enter()
