import re

from ikabot.bot.autoPirateBot import AutoPirateBot
from ikabot.config import isWindows
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, daysHoursMinutes, decodeUnicodeEscape, enter, \
    printTable
from ikabot.helpers.ikabotProcessListManager import run
from ikabot.helpers.telegram import Telegram
from ikabot.helpers.userInput import askUserYesNo, read
from ikabot.helpers.piracy import findCityWithTheBiggestPiracyFortress, \
    getPiracyTemplateData
from ikabot.web.ikariamService import IkariamService


def autoPiracyBotConfigurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    if not isWindows:
        path = run('which nslookup')
        is_installed = re.search(r'/.*?/nslookup', path) is not None
        if is_installed is False:
            print('you must first install nslookup')
            enter()
            return

    print(Colours.Text.Light.YELLOW)
    print('⚠️ USING THIS FEATURE WILL EXPOSE YOUR IP ADDRESS TO A THIRD PARTY FOR CAPTCHA SOLVING ⚠️')
    print(Colours.Text.RESET)
    print()

    great_pirate_city = findCityWithTheBiggestPiracyFortress(ikariam_service)
    if great_pirate_city is None:
        print("Well, no pirate fortress found. Sorry.")
        enter()
        return

    template_data = getPiracyTemplateData(ikariam_service, great_pirate_city['id'])

    bot_config = {
        'cityId': great_pirate_city['id'],
    }

    print("What type of automation you want?")
    print(" 1) Fixed number of piracy missions")
    print(" 2) Regular Day/Night missions")
    if read(min=1, max=2, digit=True) == 1:
        bot_config['type'] = 'fixed number'
        bot_config['missionBuildingLevel'] = __select_piracy_mission(template_data)

        print()
        bot_config['totalMissions'] = read(
            msg="Enter the number of missions you would like me to do (min=1): ",
            min=1,
        )

        print()
        bot_config['notifyWhenFinished'] = askUserYesNo("Would you like to be notified when I'm done with the pirating")

        objective = '{} x {}'.format(
            bot_config['totalMissions'],
            __get_mission_formatted_duration(template_data, bot_config['missionBuildingLevel']),
        )

    else:
        bot_config['type'] = 'daily'
        bot_config['dailyScheduleConfig'] = __select_schedule_time(
            template_data, 'day', 9, 19
        )
        bot_config['nightlyScheduleConfig'] = __select_schedule_time(
            template_data, 'night', 20, 8
        )

        objective = '[{}-{}]x({})/[{}-{}]x({})'.format(
            bot_config['dailyScheduleConfig']['startHour'],
            bot_config['dailyScheduleConfig']['endHour'],
            __get_mission_formatted_duration(template_data, bot_config['dailyScheduleConfig']['missionBuildingLevel']),
            bot_config['nightlyScheduleConfig']['startHour'],
            bot_config['nightlyScheduleConfig']['endHour'],
            __get_mission_formatted_duration(template_data, bot_config['nightlyScheduleConfig']['missionBuildingLevel']),
        )

    print()
    if askUserYesNo("Would you like to convert some capture points after each mission"):
        _all = 'all'
        _mission = 'mission'
        _over = 'over'
        print("Type {} for all available capture points".format(_all))
        print("Type {} for capture points from the executed mission".format(_mission))
        print("Type {} to convert all the capture points above certain threshold".format(_over))
        print('Type any number, to convert exact amount')
        bot_config['convertPoints'] = read(min=1, additionalValues=[_all, _mission, _over], digit=True)
        if bot_config['convertPoints'] == _over:
            _default_over = 7000
            bot_config['convertPoints'] = '{}-{}'.format(
                _over,
                read(min=1, digit=True, default=_default_over,
                     msg='Enter the minimum pirate points that you must have after (default: {})'.format(_default_over))
            )

    print()
    bot_config['maxBreakTime'] = read(min=0, digit=True, msg="Enter the maximum additional waiting time between consecutive missions in seconds. (min = 0) ")

    print('YAAAAAR!')

    AutoPirateBot(ikariam_service, bot_config).start(
        action='Auto Pirating',
        objective=objective,
        target_city=great_pirate_city['name'],
    )

    enter()


def __select_piracy_mission(template_data, additional_select_message=''):
    """
    Returns mobile pic of the selected available mission
    :param template_data: dict[] ->  fortress template data
    :param additional_select_message: str -> additional text to show the user
    :return: int
    """
    __missions_table_config = [
        {}
    ]

    print()
    print('Select privacy missions{}:'.format(additional_select_message))
    missions = {}
    missions_count = 0
    missions_table = []
    for mission_index, mission in enumerate(template_data['pirateCaptureLevels']):
        if mission['buildingLevel'] <= template_data['buildingLevel']:
            missions_count += 1
            mission['id'] = "{})".format(missions_count)
            missions[missions_count] = mission['buildingLevel']
            missions_table.append(mission)

    printTable(
        table_config=[
            {'key': 'id', 'title': '#'},
            {'key': 'name', 'title': 'Mission Name', 'fmt': decodeUnicodeEscape},
            {'key': 'capturePoints', 'title': 'Capture Points', 'fmt': addThousandSeparator},
            {'key': 'gold', 'title': 'Gold', 'fmt': addThousandSeparator},
            {'key': 'duration', 'title': 'Duration', 'fmt': lambda x: daysHoursMinutes(x)},
        ],
        table_data=missions_table,
        row_additional_indentation='  '
    )

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
    print()
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

    print()
    print("I'll operate with the {} config from {} including to {} including".format(
        schedule_type, schedule['startHour'], schedule['endHour']
    ))

    schedule['missionBuildingLevel'] = __select_piracy_mission(
        template_data,
        ' at {} time'.format(schedule_type)
    )

    return schedule


def __get_mission_formatted_duration(template_data, mission_building_level):
    """
    Get the formatted duration of the mission
    :param template_data: dict[] ->  fortress template data
    :param mission_building_level: int -> building level of the mission
    :return: str -> formatted mission duration
    """
    for mission in template_data['pirateCaptureLevels']:
        if mission['buildingLevel'] == mission_building_level:
            return daysHoursMinutes(mission['duration']).replace(' ', '')
    return 'Unknown mission duration'
