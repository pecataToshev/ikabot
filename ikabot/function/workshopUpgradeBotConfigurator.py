#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.workshopUpgradeBot import WorkshopUpgradeBot
from ikabot.function.workshop import extract_units_data
from ikabot.helpers.buildings import choose_city_with_building, get_building_info
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, decodeUnicodeEscape, enter, printTable
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.web.ikariamService import IkariamService


def workshop_upgrade_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    """
    Configure and start the workshop upgrade bot
    """
    banner()
    
    # Select city with workshop
    selected_building_data = choose_city_with_building(ikariam_service, 'workshop')
    if selected_building_data is None:
        return

    (city, building, data) = selected_building_data

    banner()
    print('Workshop in: {}'.format(city['name']))
    print()

    # Get current workshop data
    change_view_data = data[1][1][1]
    has_upgrade, units = extract_units_data(change_view_data)

    if has_upgrade:
        print("There's currently an upgrade in progress. The bot will wait for it to complete.")
        print()

    # Display available units
    def __determine_action_color(action: str, row: dict):
        if row['insufficientResources'] or has_upgrade:
            return Colours.Text.YELLOW
        if row['canUpgrade']:
            return Colours.Text.GREEN
        else:
            return Colours.Text.RED

    printTable(
        table_config=[
            {'title': 'ID', 'useDataRowIndexForValue': lambda data_index: data_index + 1,
             'setColour': __determine_action_color},
            {'key': 'tableName', 'title': 'Name', 'fmt': decodeUnicodeEscape, 'align': '<'},
            {'key': 'glass', 'title': 'Glass', 'setColour': lambda v, r: Colours.MATERIALS[3],
             'fmt': addThousandSeparator},
            {'key': 'gold', 'title': 'Gold', 'fmt': addThousandSeparator},
            {'key': 'time', 'title': 'Upgrade Time', 'align': '^'},
            {'key': 'upgrade', 'title': 'Upgrade', 'fmt': decodeUnicodeEscape},
            {'key': 'action', 'title': 'Action', 'fmt': decodeUnicodeEscape, 'setColour': __determine_action_color},
        ],
        table_data=units,
        row_additional_indentation='  ',
        missing_value='',
        print_row_separator=lambda row_index: row_index % 2 == 0
    )

    # Get unique unit names (without duplicates for different improvements)
    unique_units = {}
    for unit in units:
        if unit['name'] not in unique_units:
            unique_units[unit['name']] = {
                'name': unit['name'],
                'type': unit['type'],
                'can_upgrade': any(u['canUpgrade'] for u in units if u['name'] == unit['name']),
                'all_upgraded': all(not u['canUpgrade'] and not u['insufficientResources'] 
                                   for u in units if u['name'] == unit['name'])
            }

    # Let user select which units to target
    print('\nSelect which units/fleets to target for upgrades:')
    print('(Enter unit IDs separated by commas, or "all" for all units)')
    print()
    
    unit_list = list(unique_units.keys())
    for idx, unit_name in enumerate(unit_list, 1):
        unit_info = unique_units[unit_name]
        status = ''
        if unit_info['all_upgraded']:
            status = ' [Fully Upgraded]'
        elif not unit_info['can_upgrade']:
            status = ' [Cannot Upgrade]'
        print('({}) {} - {}{}'.format(idx, decodeUnicodeEscape(unit_name), unit_info['type'], status))

    print()
    selection = read(msg='Selection: ', empty=False)
    
    target_units = []
    if selection.lower() == 'all':
        target_units = unit_list
    else:
        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            target_units = [unit_list[i-1] for i in indices if 1 <= i <= len(unit_list)]
        except (ValueError, IndexError):
            print('Invalid selection')
            enter()
            return

    if len(target_units) == 0:
        print('No units selected')
        enter()
        return

    banner()
    print('Selected units for upgrade:')
    for unit_name in target_units:
        print('  - {}'.format(decodeUnicodeEscape(unit_name)))
    print()

    # Ask about telegram notification
    notify_on_no_resources = askUserYesNo('Send telegram notification when resources are insufficient?')

    banner()
    print('Bot Configuration:')
    print('  City: {}'.format(city['name']))
    print('  Target Units: {}'.format(len(target_units)))
    print('  Telegram Notifications: {}'.format('Yes' if notify_on_no_resources else 'No'))
    print()
    print('The bot will:')
    print('  - Upgrade units in order of lowest resource cost (glass + gold)')
    print('  - Wait for upgrades to complete')
    print('  - Wait random time (1-5 minutes) after each upgrade')
    print('  - Stop when all upgrades are complete or resources are insufficient')
    print()

    if not askUserYesNo('Start workshop upgrade bot?'):
        return

    # Start the bot
    WorkshopUpgradeBot(
        ikariam_service=ikariam_service,
        bot_config={
            'city': city,
            'building': building,
            'target_units': target_units,
            'notify_on_no_resources': notify_on_no_resources,
        }
    ).start(
        action='Workshop Upgrades',
        objective='Upgrade {} units'.format(len(target_units)),
        target_city=city['name']
    )
    
    print('Workshop upgrade bot started in {}'.format(city['name']))
    enter()
