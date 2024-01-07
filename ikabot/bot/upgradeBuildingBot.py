#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import time
import traceback
from enum import Enum

from ikabot.config import actionRequest, city_url
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.getJson import getCity
from ikabot.helpers.planRoutes import getMinimumWaitingTime
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal


class StartBuildingUpgradeResult(Enum):
    OK = 'ok',
    INSUFFICIENT_RESOURCES = 'insufficient resources',
    REPORTING_NOT_BUSY = 'reporting not busy',


def startUpgradeBuilfingBot(session, bot_config):
    """
    Performs upgrade of the building.
    :param session: ikabot.web.session.Session
    :param bot_config: dict[] -> bot config
    :return: void
    """
    set_child_mode(session)
    logging.info("Starting upgrading building with the following config: %s", bot_config)

    info = 'Upgrade building City: {}, Building: {}, From {:d}, to {:d}'.format(
        bot_config['cityName'],
        bot_config['building']['name'],
        bot_config['building']['level'],
        bot_config['building']['targetLevel'],
    )
    setInfoSignal(session, info)

    try:
        __expand_building(session, bot_config['cityId'], bot_config['building'])

    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()


def __expand_building(session, city_id, building):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    city_id : int
    building : dict[]
    """
    current_level = __get_building_current_level(building)
    position = building['position']

    session.wait(5, max_random=15, info='Waiting to avoid race conditions with sendResourcesNeeded')

    while current_level < building['upgradeTo']:
        [started, city] = __start_building_upgrade(session, city_id, position)

        building = city['position'][position]
        current_level = __get_building_current_level(building)

        if started != StartBuildingUpgradeResult.OK:
            msg = '{} (lvl{}) in {} could not reach target level {} due to {}!'.format(
                building['positionAndName'], building['level'], city['cityName'], building['upgradeTo'], started
            )
            logging.info(msg)
            sendToBot(session, msg)
            return

        msg = '{}: The building {} is being extended to level {:d}.'.format(
            city['cityName'], building['positionAndName'], building['level'] + 1)
        logging.info(msg)

    msg = '{}: The building {} finished extending to level: {:d}.'.format(
        city['cityName'], building['positionAndName'], building['level'] + 1)
    logging.info(msg)


def __start_building_upgrade(session, city_id, position):
    city = __wait_ongoing_construction(session, city_id)
    building = city['position'][position]

    if not building['canUpgrade']:
        incoming_ships_time = getMinimumWaitingTime(session)
        if incoming_ships_time == 0:
            # No ships are coming...
            return [StartBuildingUpgradeResult.INSUFFICIENT_RESOURCES, city]

        session.wait(incoming_ships_time + 5, 'Waiting the ships to arrive')
        return __start_building_upgrade(session, city_id, position)

    session.post(params={
        'action': 'CityScreen',
        'function': 'upgradeBuilding',
        'actionRequest': actionRequest,
        'cityId': city_id,
        'position': position,
        'level': building['level'],
        'activeTab': 'tabSendTransporter',
        'backgroundView': 'city',
        'currentCityId': city_id,
        'templateView': building['building'],
        'ajax': '1'
    })

    city = getCity(session.get(city_url + city_id))
    building = city['position'][position]
    if building['isBusy'] is False:
        return [StartBuildingUpgradeResult.REPORTING_NOT_BUSY, city]

    return [StartBuildingUpgradeResult.OK, city]


def __get_building_current_level(building):
    current_level = building['level']
    if building['isBusy']:
        current_level += 1
    return current_level


def __wait_ongoing_construction(session, city_id):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    city_id : int

    Returns
    -------
    city : dict
    """
    while True:
        city = getCity(session.get(city_url + city_id))

        construction_buildings = [building for building in city['position'] if 'completed' in building]
        if len(construction_buildings) == 0:
            return city

        construction_building = construction_buildings[0]
        construction_time = construction_building['completed']

        current_time = int(time.time())
        final_time = int(construction_time)
        seconds_to_wait = final_time - current_time

        msg = 'I wait {} to get to level {:d}'.format(construction_building['positionAndName'],
                                                      construction_building['level'] + 1)
        session.wait(seconds_to_wait + 5, msg, max_random=15)

