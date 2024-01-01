from ikabot.bot.autoPirateBot import startAutoPirateBot
from ikabot.helpers.pedirInfo import *
from ikabot.helpers.piracy import findCityWithTheBiggestPiracyFortress, \
  getPiracyTemplateData
from ikabot.helpers.varios import daysHoursMinutes


def autoPiracyBotConfigurator(session, event, stdin_fd, predetermined_input):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    banner()

    great_pirate_city_id = findCityWithTheBiggestPiracyFortress(session)
    if great_pirate_city_id is None:
        print("Well, no pirate fortress found. Sorry.")
        enter()
        event.set()
        return

    template_data = getPiracyTemplateData(session, great_pirate_city_id)

    bot_config = {
        'cityId': great_pirate_city_id
    }

    print("What type of automation you want?")
    print(" 1) Fixed number of piracy missions")
    print(" 2) Regular Day/Night missions")
    if read(min=1, max=2, digit=True) == 1:
        bot_config['type'] = 'fixed number'
        bot_config['missionMobilePic'] = __select_piracy_mission(template_data)
    else:
        bot_config['type'] = 'daily'
        bot_config['dailyScheduleConfig'] = __select_schedule_time(
            template_data, 'day', 9, 19
        )
        bot_config['nightlyScheduleConfig'] = __select_schedule_time(
            template_data, 'night', 20, 8
        )

    if askUserYesNo("Would you like to convert some capture points after each mission"):
        _all = 'all'
        _mission = 'mission'
        print("Type {} for all available capture points".format(_all))
        print("Type {} for capture points from the previous mission".format(_mission))
        print('Type any number, to convert exact amount')
        bot_config['convertPoints'] = read(min=1, additionalValues=[_all, _mission])

    bot_config['maxBreakTime'] = read(min=0, digit=True, msg="Enter the maximum additional waiting time between consecutive missions in seconds. (min = 0)")

    print('YAAAAAR!')

    enter()
    event.set()

    startAutoPirateBot(session, bot_config)


def __select_piracy_mission(template_data, additional_select_message=''):
    """
    Returns mobile pic of the selected available mission
    :param template_data: dict[] ->  fortress template data
    :param additional_select_message: str -> additional text to show the user
    :return: str
    """
    print('Select privacy missions{}:'.format(additional_select_message))
    missions = {}
    missions_count = 0
    for mission_index, mission in enumerate(template_data['pirateCaptureLevels']):
        if mission['buildingLevel'] >= template_data['buildingLevel']:
            missions_count += 1
            mission[missions_count] = mission['mobilePic']
            print(" {}) {} (points: {}, gold: {}, duration: {})".format(
                missions_count,
                mission['name'],
                mission['capturePoints'],
                mission['gold'],
                daysHoursMinutes(mission['duration'], include_seconds=True),
            ))

    selected = read(min=1, max=missions_count, digit=True)
    return missions[selected]


def __select_schedule_time(template_data, schedule_type, default_start, default_end):
    """
    Returns schedule config with mission
    :param template_data: dict[] ->  fortress template data
    :param schedule_type: str -> type of the schedule
    :param default_start: int -> default start hour
    :param default_end: int -> default end hour
    :return: dict[] with the schedule
    """
    print("Let's configure the {} time schedule:".format(schedule_type))

    schedule = {
        'type': schedule_type
    }

    operating_hours = default_end - default_start + 1
    if default_start > default_end:
        operating_hours = 24 - default_start + default_end + 1
    print("At which hours should I operate at {} time? "
          "(Default: {} hours from {} till {})".format(
            schedule_type, operating_hours, default_start, default_end)
    )
    schedule['startHour'] = read(min=0, max=23, digit=True, msg='From: ',
                                 default=default_start)
    schedule['endHour'] = read(min=0, max=23, digit=True, msg='Till: ',
                               default=default_end)

    print("I'll operate with the {} config from {} including to {} including".format(
        schedule_type, schedule['startHour'], schedule['endHour']
    ))

    schedule['missionMobilePic'] = __select_piracy_mission(
        template_data,
        ' at {} time'.format(schedule_type)
    )

    return schedule

