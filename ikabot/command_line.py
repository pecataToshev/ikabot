#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import sys
import time
import traceback

from ikabot.function.activateMiracleBotConfigurator import activate_miracle_bot_configurator
from ikabot.function.attackBarbariansBotConfigurator import attack_barbarians_bot_configurator
from ikabot.function.attacksMonitoringBotConfigurator import configure_alert_attacks_monitoring_bot
from ikabot.function.autoPiracyBotConfigurator import autoPiracyBotConfigurator
from ikabot.function.buyResourcesBotConfigurator import buy_resources_bot_configurator
from ikabot.function.buyShip import buy_ships
from ikabot.function.conductExperimentBotConfigurator import configure_conduct_experiment_bot
from ikabot.function.constructBuilding import constructBuilding
from ikabot.function.decaptchaConf import decaptchaConf
from ikabot.function.distributeResourcesBotConfigurator import distribute_resources_bot_configurator
from ikabot.function.donationBotConfigurator import donation_bot_configurator
from ikabot.function.dumpWorld import dump_world_bot_configurator, view_dump
from ikabot.function.getStatus import getStatus
from ikabot.function.getStatusImproved import getStatusForAllCities
from ikabot.function.importExportCookie import exportCookie, importCookie
from ikabot.function.islandMonitoringBotConfigurator import island_monitoring_bot_configurator
from ikabot.function.islandWorkplaces import islandWorkplaces
from ikabot.function.killTasks import kill_tasks
from ikabot.function.loginDailyBotConfigurator import login_daily_bot_configurator
from ikabot.function.miracle_donate import miracle_donate
from ikabot.function.proxyConf import proxyConf, show_proxy
from ikabot.function.sellResourcesBotConfigurator import sell_resources_bot_configurator
from ikabot.function.tavern import use_tavern
from ikabot.function.shipMovements import shipMovements
from ikabot.function.showPiracyInfo import showPiracyInfo
from ikabot.function.stationArmy import stationArmy
from ikabot.function.studies import study
from ikabot.function.telegramFunctions import test_telegram_bot, update_telegram_bot
from ikabot.function.trainArmyBotConfigurator import train_army_bot_configurator
from ikabot.function.transportGoodsBotConfigurator import transport_goods_bot_configurator
from ikabot.function.update import update
from ikabot.function.upgradeBuildingBotConfigurator import upgrade_building_bot_configurator
from ikabot.function.vacationMode import vacationMode
from ikabot.function.wineMonitoringBotConfigurator import configure_wine_monitoring_bot
from ikabot.function.workshop import use_workshop
from ikabot.helpers.checkForUpdate import checkForUpdate
from ikabot.helpers.gui import banner, clear, enter, formatTimestamp
from ikabot.helpers.ikabotProcessListManager import IkabotProcessListManager
from ikabot.helpers.userInput import read

__function_refresh = 'refresh'
__function_exit = 'exit'

__command_back = ['Back', __function_refresh]

_global_menu = [
    ['Exit', __function_exit],
    ['Refresh process info', __function_refresh],
    ['Construction', [
        __command_back,
        ['Building Upgrades', upgrade_building_bot_configurator],
        ['Construct building', constructBuilding],
    ]],
    ['Resources & Donations', [
        __command_back,
        ['Send resources', transport_goods_bot_configurator],
        ['Distribute resources', distribute_resources_bot_configurator],
        ['Donate once', islandWorkplaces],
        ['Donate automatically', donation_bot_configurator],
    ]],
    ['Cities & Status', [
        __command_back,
        ['Simplified', getStatus],
        ['Combined', getStatusForAllCities],
    ]],
    ['Alerts / Monitoring', [
        __command_back,
        ['Alert attacks', configure_alert_attacks_monitoring_bot],
        ['Alert wine running out', configure_wine_monitoring_bot],
        ['Monitor islands', island_monitoring_bot_configurator],
    ]],
    ['Marketplace', [
        __command_back,
        ['Buy resources', buy_resources_bot_configurator],
        ['Sell resources', sell_resources_bot_configurator],
    ]],
    ['Miracle', [
        __command_back,
        ['Activate Miracle', activate_miracle_bot_configurator],
        ['Donate to Miracle', miracle_donate],
    ]],
    ['Military actions', [
        __command_back,
        ['Train Army', train_army_bot_configurator],
        ['Send Troops/Ships', stationArmy],
        ['Attack barbarians', attack_barbarians_bot_configurator],
    ]],
    ['See movements', shipMovements],
    ['Piracy', [
        __command_back,
        ['Show Piracy Stats', showPiracyInfo],
        ['Configure Auto-Pirate Bot', autoPiracyBotConfigurator],
    ]],
    ['Academy', [
        __command_back,
        ['Study', study],
        ['Conduct Experiments', configure_conduct_experiment_bot],
    ]],
    ['Taverns', use_tavern],
    ['Workshops', use_workshop],
    ['Buys Ships', buy_ships],
    ['Game Account Functions', [
        __command_back,
        ['Login daily', login_daily_bot_configurator],
        ['Activate vacation mode', vacationMode],
        ['Dump / View world', [
            __command_back,
            ['Create new dump', dump_world_bot_configurator],
            ['Load existing dump', view_dump],
        ]],
    ]],
    ['Options / Settings', [
        __command_back,
        ['Configure Proxy', proxyConf],
        ['Telegram Bot', [
            __command_back,
            ['Change bot data', update_telegram_bot],
            ['Test message the bot', test_telegram_bot],
        ]],
        ['Kill tasks', kill_tasks],
        ['Configure captcha resolver', decaptchaConf],
        ['Cookies', [
            __command_back,
            ['Import', importCookie],
            ['Export', exportCookie],
        ]],
        ['Update Ikabot', update],
    ]],
]


def choose_from_menu(menu_options, prefix=''):
    for ind, option in enumerate(menu_options):
        print(prefix, "{: >3})".format(ind), option[0])
    selected = read(min=0, max=len(menu_options)-1, digit=True)

    print()
    [name, fn] = menu_options[selected]
    print(prefix, 'Selected {}) {}'.format(selected, name))
    if type(fn) is list:
        return choose_from_menu(fn, prefix + '  ')

    return fn


def menu(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    checkForUpdate()
    show_proxy(db)
    process_list_manager = IkabotProcessListManager(db)
    consecutive_keyboard_interruptions = False

    while True:
        banner()

        print("now: ", formatTimestamp(time.time()))
        process_list_manager.print_proces_table()

        try:
            selected = choose_from_menu(_global_menu)
            logging.debug('Selected from the menu: %s',
                          selected.__name__ if type(selected) is not str else selected)
            consecutive_keyboard_interruptions = False

            if selected == __function_exit:
                # Perform exit of the app
                break

            if selected == __function_refresh:
                # we just need to refresh the menu
                continue

            # we've selected a function, let's execute it
            selected(ikariam_service, db, telegram)
        except KeyboardInterrupt:
            logging.debug('Received keyboard interruption in command line, consecutive_keyboard_interruptions: %s',
                          consecutive_keyboard_interruptions)
            if consecutive_keyboard_interruptions:
                break
            # First time. We're going to refresh the menu
            consecutive_keyboard_interruptions = True
            continue

        except Exception as e:
            msg = 'Error...\nMessage: {}\nCause: {}'.format(
                str(e), traceback.format_exc()
            )
            print(msg)
            logging.error(msg)
            enter()

    if consecutive_keyboard_interruptions:
        logging.debug('Forcefully quiting the command centre')
        sys.exit(1)

    clear()
    logging.debug('Gracefully exiting the command centre')
    sys.exit(0)
