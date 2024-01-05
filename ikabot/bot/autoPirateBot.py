import datetime
import logging
import traceback

from ikabot.config import actionRequest
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.catpcha import resolveCaptcha
from ikabot.helpers.piracy import getPiracyTemplateData, convertCapturePoints
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal


__MAXIMUM_PIRATE_MISSION_START_ATTEMPTS=20

def startAutoPirateBot(session, piracy_config):
    """
    Performs auto pirate scheduled tasks.
    :param session: ikabot.web.session.Session
    :param piracy_config: dict[] -> piracy bot config
    :return: void
    """
    set_child_mode(session)
    logging.info("Starting auto pirating with the following config: %s", piracy_config)

    daily_type = piracy_config['type'] == 'daily'

    info = '\nI execute {} piracy missions\n'.format(piracy_config['type'])
    setInfoSignal(session, info)

    try:
        if daily_type:
            __execute_piracy_daily_missions(session, piracy_config)
        else:
            __execute_piracy_tasks(session, piracy_config)

    except Exception as e:
        msg = 'Error in:\n{}\nCause:\n{}'.format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()


def __get_time_to_sleep_to_next_given_hour(now, given_hour):
    """
    Returns seconds till next time with the given hour.
    :param now: datetime -> current time
    :param given_hour: int -> the wanted hour
    :return: int
    """
    expected_time = now.replace(hour=given_hour,
                                minute=0, second=0, microsecond=0)
    if expected_time < now:
        expected_time += datetime.timedelta(days=1)

    return (expected_time - now).total_seconds()


def __execute_piracy_daily_missions(session, piracy_config):
    """
    Performs piracy tasks based on daytime.
    :param session: ikabot.web.session.Session
    :param piracy_config: dict[] -> piracy bot config
    :return: void
    """
    day_config = piracy_config['dailyScheduleConfig']
    night_config = piracy_config['nightlyScheduleConfig']

    last_mission_type = None
    while True:
        now = datetime.datetime.now()

        if __is_config_active(now, day_config):
            logging.debug('Executing daily mission')
            last_mission_type = 'daily'
            __execute_piracy_mission(
                session=session,
                city_id=piracy_config['cityId'],
                mission_building_level=day_config['missionBuildingLevel'],
                convert_points_to_strength=piracy_config.get('convertPoints', None),
                additional_message='@daily',
            )
            __perform_break_between_missions(
                session,
                piracy_config['maxBreakTime'],
                'Daily missions'
            )

        elif __is_config_active(now, night_config):
            if last_mission_type == 'nightly':
                # we've executed one night mission. sleep till day start
                total_sleep_time = __get_time_to_sleep_to_next_given_hour(now, day_config['startHour'])
                session.wait(
                    total_sleep_time,
                    "Sleeping until day start @{}h".format(day_config['startHour'])
                )
            else:
                logging.debug('Executing nightly mission')
                __execute_piracy_mission(
                    session=session,
                    city_id=piracy_config['cityId'],
                    mission_building_level=night_config['missionBuildingLevel'],
                    convert_points_to_strength=piracy_config.get('convertPoints', None),
                    additional_message='@nightly'
                )

            last_mission_type = 'nightly'

        else:
            logging.debug("We're in a config gap")
            # We're in a config gap. Sleep until closest start hour
            seconds_to_day_start = __get_time_to_sleep_to_next_given_hour(now, day_config['startHour'])
            seconds_to_night_start = __get_time_to_sleep_to_next_given_hour(now, night_config['startHour'])

            if seconds_to_day_start <= seconds_to_night_start:
                session.wait(
                    seconds_to_day_start,
                    "Schedule gap. Sleeping until day start @{}h".format(day_config['startHour'])
                )
            else:
                session.wait(
                    seconds_to_night_start,
                    "Schedule gap. Sleeping until night start @{}h".format(night_config['startHour'])
                )


def __execute_piracy_tasks(session, piracy_config):
    """
    Performs auto pirate scheduled tasks.
    :param session: ikabot.web.session.Session
    :param piracy_config: dict[] -> piracy bot config
    :return: void
    """
    total_missions = piracy_config['totalMissions']

    for task_index in range(total_missions):
        __execute_piracy_mission(
            session=session,
            city_id=piracy_config['cityId'],
            mission_building_level=piracy_config['missionBuildingLevel'],
            convert_points_to_strength=piracy_config.get('convertPoints', None),
            additional_message='Mission {}/{}'.format(task_index + 1,
                                                      total_missions)
        )
        __perform_break_between_missions(
            session,
            piracy_config['maxBreakTime'],
            'After mission {}/{}'.format(task_index + 1, total_missions)
        )

    logging.info("Successfully executed %d piracy missions",
                 total_missions)

    if piracy_config['notifyWhenFinished']:
        sendToBot(session, "I'm done with pirating")


def __is_config_active(given_time, schedule_config):
    """
    Determines if the config is active in the given time
    :param given_time: datetime.datetime
    :param schedule_config: dict[]
    :return: bool
    """
    current_hour = int(given_time.strftime("%H"))
    _s = schedule_config['startHour']
    _e = schedule_config['endHour']
    return _s < _e and _s <= current_hour <= _e \
        or _s > _e and (current_hour <= _e or _s <= current_hour)


def __perform_break_between_missions(session, max_break_time, additional_info):
    """
    Performs break between two consecutive piracy missions.
    :param session: ikabot.web.session.Session
    :param max_break_time: int -> breaks between consecutive missions
    :param additional_info: str -> additional info message
    :return: void
    """
    if max_break_time > 0:
        session.wait(
            seconds=1,
            info='Waiting between missions. ' + additional_info,
            max_random=max_break_time-1)


def __get_template_data_and_wait_ongoing_mission(session, city_id):
    """
    Changes view to city and opens the piracy fortress view. Then returns the
    template data of the response
    :param session: ikabot.web.session.Session
    :param city_id: int -> city with the fortress
    :return: dict[]
    """
    data = getPiracyTemplateData(session, city_id)
    if data['hasOngoingMission']:
        session.wait(data['ongoingMissionTimeRemaining'],
                     'Found unexpected mission. Waiting it to end.',
                     max_random=5)
        return __get_template_data_and_wait_ongoing_mission(session, city_id)

    return data


def __execute_piracy_mission(
    session,
    city_id,
    mission_building_level,
    convert_points_to_strength,
    additional_message,
    captcha=None,
    remaining_attempts=__MAXIMUM_PIRATE_MISSION_START_ATTEMPTS,
):
    """
    Executes piracy mission and handles captcha.
    :param session: ikabot.web.session.Session
    :param city_id: int -> city with the fortress
    :param mission_building_level: int -> the building level of the mission
    :param convert_points_to_strength: int/str -> conversion configuration
    :param additional_message: str -> additional message in the statuses
    :param captcha: str -> resolved captcha
    :param remaining_attempts: times to try id captcha is not solved
    :return: void
    """
    if remaining_attempts <= 0:
        raise Exception('Failed to start the mission too many times. Terminating')

    data = __get_template_data_and_wait_ongoing_mission(session, city_id)
    mission = [p for p in data['pirateCaptureLevels'] if p['buildingLevel'] == mission_building_level][0]

    if mission['buildingLevel'] > data['buildingLevel']:
        _msg = 'This piracy mission ({}) requires {} building level' \
               'but found {}'.format(mission['name'],
                                     mission['buildingLevel'],
                                     data['buildingLevel'], )
        raise Exception(_msg)

    params = {
        'action': 'PiracyScreen',
        'function': 'capture',
        'buildingLevel': mission['buildingLevel'],
        'view': 'pirateFortress',
        'cityId': city_id,
        'position': '17',
        'activeTab': 'tabBootyQuest',
        'backgroundView': 'city',
        'currentCityId': city_id,
        'templateView': 'pirateFortress',
        'actionRequest': actionRequest,
        'ajax': '1'
    }
    if captcha is not None:
        params.update({
            'captchaNeeded': '1',
            'captcha': captcha,
        })

    # try to execute the pirate mission
    html = session.post(params=params, noIndex=captcha is not None)
    if 'function=createCaptcha' not in html \
            and '"showPirateFortressShip":0' in html:

        # execution is successful, go get some sleep
        session.wait(mission['duration'],
                     'Executing piracy mission {}. {}'.format(mission['name'],
                                                              additional_message),
                     5)

        if convert_points_to_strength is not None:
            if convert_points_to_strength == 'mission':
                convert_points_to_strength = mission['capturePoints']
            convertCapturePoints(session, city_id, convert_points_to_strength)

        return

    if 'function=createCaptcha' not in html:
        logging.warning('Mission has not started, but captcha not required. '
                        'Retrying the mission execution')
        return __execute_piracy_mission(
            session=session,
            city_id=city_id,
            mission_building_level=mission_building_level,
            convert_points_to_strength=convert_points_to_strength,
            additional_message=additional_message,
            captcha=None,
            remaining_attempts=remaining_attempts-1,
        )

    session.setProcessInfo('We have to solve some captcha. Let me handle that')
    captcha = None  # well, captcha failed, let's generate a new one
    while (captcha is None or captcha == 'Error') and remaining_attempts > 0:
        remaining_attempts -= 1
        logging.info("Found captcha. Trying to resolve it. "
                     "%d attempts remaining", remaining_attempts)

        picture = session.get('action=Options&function=createCaptcha',
                              fullResponse=True).content
        captcha = resolveCaptcha(session, picture)

        logging.info("Resolved captcha to %s", captcha)

    # captcha has been resolved, let's try again.
    # or no more remaining attempts
    return __execute_piracy_mission(
        session=session,
        city_id=city_id,
        mission_building_level=mission_building_level,
        convert_points_to_strength=convert_points_to_strength,
        additional_message=additional_message,
        captcha=captcha,
        remaining_attempts=remaining_attempts,
    )

