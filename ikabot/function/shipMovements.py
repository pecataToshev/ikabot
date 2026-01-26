#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import re
import time
from decimal import Decimal

from ikabot.config import materials_names, materials_names_tec
from ikabot.helpers.citiesAndIslands import getCurrentCityId
from ikabot.helpers.getJson import parse_int
from ikabot.helpers.gui import (Colours, addThousandSeparator, banner,
                                daysHoursMinutes, enter, printTable, decodeUnicodeEscape, formatTimestamp)
from ikabot.helpers.naval import (TransportShip,
                                  get_military_and_see_movements,
                                  get_transport_ships_size, getAvailableShips,
                                  getTotalShips)
from ikabot.helpers.userInput import read


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
        if 'transport' not in mov['cssClass'] and 'freighter' not in mov['cssClass']:
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
    ship_size = get_transport_ships_size(ikariam_service, getCurrentCityId(ikariam_service), TransportShip.TRANSPORT_SHIP)
    while True:
        banner()

        print('Current time: {}'.format(formatTimestamp(time.time())))
        # TODO: FIX multiple calls to the get
        print('Ships {:d}/{:d}\n'.format(getAvailableShips(ikariam_service), getTotalShips(ikariam_service)))

        movements = get_military_and_see_movements(ikariam_service)
        time_now = int(time.time())

        if len(movements) == 0:
            print('There are no movements')
        else:
            table_data = []
            for movement in movements:
                # Extract info
                troops = parse_int(movement['army'].get('amount', 0))
                transport_ships = 0
                freighter_ships = 0
                military_ships = 0
                fleet_info = movement.get('fleet', {})
                ships_list = fleet_info.get('ships', [])
                if ships_list:
                    for s in ships_list:
                        amt = parse_int(s.get('amount', 0))
                        css = s.get('cssClass', '')
                        if 'ship_transport' == css:
                            transport_ships += amt
                        elif 'freighter' in css:
                            freighter_ships += amt
                        else:
                            military_ships += amt
                else:
                    # Fallback to total amount
                    total_fleet = parse_int(fleet_info.get('amount', 0))
                    if movement['isHostile'] or troops > 0 or isHostile(movement):
                        military_ships = total_fleet
                    else:
                        transport_ships = total_fleet

                # Cargo (Troops + Resources)
                cargo_info = []
                if troops > 0:
                    cargo_info.append('Troops: {}'.format(addThousandSeparator(troops)))

                total_load = 0
                for resource in movement.get('resources', []):
                    amount = resource['amount']
                    tradegood = resource['cssClass'].split()[1]
                    if tradegood != 'gold':
                        try:
                            index = materials_names_tec.index(tradegood)
                            res_name = materials_names[index]
                            res_color = Colours.MATERIALS[index]
                            cargo_info.append('{}{} {}{}'.format(res_color, amount, res_name, Colours.Text.RESET))
                        except (ValueError, IndexError):
                            cargo_info.append('{} {}'.format(amount, tradegood))
                    else:
                        cargo_info.append('{} {}'.format(amount, tradegood))
                    total_load += parse_int(amount)

                # Estimate ships if we have load but 0 transport ships and 0 freighters (sometimes happens if fleet info is partial)
                if transport_ships == 0 and freighter_ships == 0 and total_load > 0:
                    transport_ships = int(math.ceil((Decimal(total_load) / Decimal(ship_size))))

                # Build details string
                details = []
                # Troops moved to cargo
                if military_ships > 0:
                    details.append('Fleets: {}'.format(addThousandSeparator(military_ships)))
                if transport_ships > 0:
                    details.append('Ships: {}'.format(addThousandSeparator(transport_ships)))
                if freighter_ships > 0:
                    details.append('Freighters: {}'.format(addThousandSeparator(freighter_ships)))

                def format_city(city_data):
                    decoded_city = decodeUnicodeEscape(city_data['name'])
                    decoded_avatar = decodeUnicodeEscape(city_data['avatarName'])
                    if decoded_avatar == ikariam_service.username:
                        return decoded_city
                    return '{} ({})'.format(decoded_city, decoded_avatar)

                def get_city_color(city_data):
                    decoded_avatar = decodeUnicodeEscape(city_data['avatarName'])
                    if decoded_avatar == ikariam_service.username:
                        return Colours.Text.RESET

                    # If not hostile (no troops/warships) and not mine
                    if not isHostile(movement):
                        return Colours.Text.Light.CYAN

                    # If the movement is from an alliance member, and this city belongs to the one who started the movement
                    if movement['isSameAlliance'] and not movement['isOwnArmyOrFleet']:
                        return Colours.Text.Light.GREEN

                    # If the city owner is different from the player and it's not our city
                    return Colours.Text.Light.RED

                time_left = int(movement['eventTime']) - time_now
                abs_time = formatTimestamp(int(movement['eventTime']))

                time_color = Colours.Text.Light.YELLOW if time_left < 120 else ''
                time_str = '{} {}({:>7})'.format(abs_time, time_color, daysHoursMinutes(time_left, add_leading_zeroes_on_smaller_unit=True))

                mission_text = movement['event']['missionText']
                mission_match = re.match(r'^(.*?) \((.*?)\)$', mission_text)
                if mission_match:
                    mission = mission_match.group(1)
                    status = mission_match.group(2)
                else:
                    mission = mission_text
                    status = ''

                mission_color = Colours.Text.RESET
                if isHostile(movement):
                    if decodeUnicodeEscape(movement['origin']['avatarName']) == ikariam_service.username:
                        mission_color = Colours.Text.Light.YELLOW + Colours.Text.Format.BOLD
                    else:
                        mission_color = Colours.Text.Light.RED + Colours.Text.Format.BOLD

                table_data.append({
                    'origin': format_city(movement['origin']),
                    'origin_color': get_city_color(movement['origin']),
                    'target': format_city(movement['target']),
                    'target_color': get_city_color(movement['target']),
                    'mission': mission,
                    'mission_color': mission_color,
                    'status': status,
                    'time': time_str,
                    'details': ', '.join(details),
                    'cargo': ', '.join(cargo_info),
                    'isHostile': movement['isHostile'],
                    'isOwn': movement['isOwnArmyOrFleet'],
                    'isAlliance': movement['isSameAlliance']
                })


            table_config = [
                {'key': 'origin', 'title': 'Origin', 'align': '<', 'setColour': lambda _, r: r['origin_color']},
                {'key': 'target', 'title': 'Destination', 'align': '<', 'setColour': lambda _, r: r['target_color']},
                {'key': 'mission', 'title': 'Mission', 'align': '<', 'setColour': lambda _, r: r['mission_color']},
                {'key': 'status', 'title': 'Status', 'align': '<'},
                {'key': 'time', 'title': 'Time', 'align': '<'},
                {'key': 'details', 'title': 'Details', 'align': '<'},
                {'key': 'cargo', 'title': 'Cargo', 'align': '<'}
            ]

            printTable(table_config, table_data, print_row_separator=lambda i: i == 0)

        print("\nActions:")
        print(" 0) Exit")
        print(" 1) Refresh")
        action = read(min=0, max=1, digit=True)
        if action == 0:
            break
