import os
import os
import sys

from ikabot import config
from ikabot.helpers.gui import addThousandSeparator, banner, bcolors, daysHoursMinutes, decodeUnicodeEscape, enter, \
    printTable
from ikabot.helpers.piracy import findCityWithTheBiggestPiracyFortress, \
    getPiracyTemplateData


def showPiracyInfo(session, event, stdin_fd, predetermined_input):
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

    try:
        banner()

        great_pirate_city = findCityWithTheBiggestPiracyFortress(session)
        template_data = getPiracyTemplateData(session, great_pirate_city)

        print('Biggest fortress level:', template_data['buildingLevel'])

        print()
        print('Crew points:', addThousandSeparator(template_data['completeCrewPoints']))
        print('      basic:', addThousandSeparator(template_data['basicCrewPoints']))
        print('        own:', addThousandSeparator(template_data['crewPoints']))
        print('      bonus:', addThousandSeparator(template_data['bonusCrewPoints']))

        print()
        print('Capture points:', addThousandSeparator(template_data['capturePoints']))

        if template_data['hasOngoingMission']:
            mission = [m for m in template_data['pirateCaptureLevels']
                       if m['buildingLevel'] == template_data['ongoingMissionLevel']][0]
            print()
            print("Ongoing mission:", decodeUnicodeEscape(mission['name']))
            print(" Capture points:", addThousandSeparator(mission['capturePoints']))
            print("           Gold:", addThousandSeparator(mission['gold']))
            print("      Time left:", daysHoursMinutes(template_data['ongoingMissionTimeRemaining']))

        if template_data['hasOngoingConvertion']:
            print()
            print('Ongoing conversion: {} points -> {} crew strength'.format(
                addThousandSeparator(template_data['ongoingConvertionCapturePoints']),
                addThousandSeparator(template_data['ongoingConvertionCrewPoints'])
            ))
            print("        Time left:", daysHoursMinutes(template_data['ongoingConvertionTimeRemaining']))


        print()
        print('Piracy Ranking:')
        print('     Time left:', daysHoursMinutes(template_data['highscoreTimeLeft']))

        printTable(
            table_config=[
                {'key': 'place', 'title': '#'},
                {'key': 'name', 'title': 'Player', 'fmt': decodeUnicodeEscape},
                {'key': 'capturePoints', 'title': 'Capture Points', 'fmt': addThousandSeparator},
                {'key': 'distance', 'title': 'Distance'},
            ],
            table_data=template_data['highscore'],
            row_color=lambda row_id: bcolors.ENDC if row_id - 1 != template_data['highscorePlayerPosition'] else bcolors.WARNING,
            row_additional_indentation='  '
        )

        enter()
    except KeyboardInterrupt:
        print('Resetting')

    event.set()
