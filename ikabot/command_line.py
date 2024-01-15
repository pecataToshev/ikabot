#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from ikabot.function.activateMiracleBotConfigurator import activate_miracle_bot_configurator
from ikabot.function.attacksMonitoringBotConfigurator import configure_alert_attacks_monitoring_bot
from ikabot.function.wineMonitoringBotConfigurator import configure_wine_monitoring_bot
from ikabot.function.attackBarbarians import attackBarbarians
from ikabot.function.autoPiracyBotConfigurator import autoPiracyBotConfigurator
from ikabot.function.buyResources import buyResources
from ikabot.function.conductExperimentBotConfigurator import configure_conduct_experiment_bot
from ikabot.helpers.checkForUpdate import checkForUpdate
from ikabot.function.constructBuilding import constructBuilding
from ikabot.function.upgradeBuildingBotConfigurator import upgrade_building_bot_configurator
from ikabot.function.decaptchaConf import decaptchaConf
from ikabot.function.distributeResources import distributeResources
from ikabot.function.donationBot import donationBot
from ikabot.function.dumpWorld import dumpWorld
from ikabot.function.getStatus import getStatus
from ikabot.function.getStatusImproved import getStatusForAllCities
from ikabot.function.importExportCookie import importCookie, exportCookie
from ikabot.function.studies import study
from ikabot.function.islandWorkplaces import islandWorkplaces
from ikabot.function.killTasks import kill_tasks
from ikabot.function.loginDailyBotConfigurator import login_daily_bot_configurator
from ikabot.function.proxyConf import proxyConf, show_proxy
from ikabot.function.islandMonitoringBotConfigurator import island_monitoring_bot_configurator
from ikabot.function.sellResources import sellResources
from ikabot.function.transportGoodsBotConfigurator import transport_goods_bot_configurator
from ikabot.function.shipMovements import shipMovements
from ikabot.function.showPiracyInfo import showPiracyInfo
from ikabot.function.stationArmy import stationArmy
from ikabot.function.testTelegramBot import testTelegramBot
from ikabot.function.trainArmy import trainArmy
from ikabot.function.update import update
from ikabot.function.vacationMode import vacationMode
from ikabot.helpers.botComm import updateTelegramData
from ikabot.helpers.gui import banner, formatTimestamp
from ikabot.helpers.ikabotProcessListManager import IkabotProcessListManager
from ikabot.helpers.pedirInfo import read

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
        ['Distribute resources', distributeResources],
        ['Donate once', islandWorkplaces],
        ['Donate automatically', donationBot],
    ]],
    ['Cities Status', [
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
        ['Buy resources', buyResources],
        ['Sell resources', sellResources],
    ]],
    ['Activate miracle', activate_miracle_bot_configurator],
    ['Military actions', [
        __command_back,
        ['Train Army', trainArmy],
        ['Send Troops/Ships', stationArmy],
        ['Attack barbarians', attackBarbarians],
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
    ['Game Account Functions', [
        __command_back,
        ['Login daily', login_daily_bot_configurator],
        ['Activate vacation mode', vacationMode],
        ['Dump / View world', dumpWorld],
    ]],
    ['Options / Settings', [
        __command_back,
        ['Configure Proxy', proxyConf],
        ['Telegram Bot', [
            __command_back,
            ['Change bot data', updateTelegramData],
            ['Test message the bot', testTelegramBot],
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

    while True:
        banner()

        print("now: ", formatTimestamp(time.time()))
        process_list_manager.print_proces_table()

        try:
            selected = choose_from_menu(_global_menu)

            if selected == __function_exit:
                # Perform exit of the app
                break

            if selected == __function_refresh:
                # we just need to refresh the menu
                continue

            # we've selected a function, let's execute it
            selected(ikariam_service, db, telegram)
        except KeyboardInterrupt:
            # we're going to refresh the menu
            pass
