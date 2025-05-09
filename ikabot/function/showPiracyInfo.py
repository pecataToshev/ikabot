import math

from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, Colours, daysHoursMinutes, decodeUnicodeEscape, enter, \
    printTable
from ikabot.helpers.piracy import findCityWithTheBiggestPiracyFortress, \
    getPiracyTemplateData
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def showPiracyInfo(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()

    great_pirate_city = findCityWithTheBiggestPiracyFortress(ikariam_service)
    template_data = getPiracyTemplateData(ikariam_service, great_pirate_city['id'])

    print('Biggest fortress level:', template_data['buildingLevel'])

    print()
    print('Crew points:', addThousandSeparator(template_data['completeCrewPoints']))
    print('      basic:', addThousandSeparator(template_data['basicCrewPoints']))
    print('        own:', addThousandSeparator(template_data['crewPoints']))
    print('      bonus:', addThousandSeparator(template_data['bonusCrewPoints']))

    print()
    print('Capture points:', addThousandSeparator(template_data['capturePoints']))

    if template_data['hasOngoingMission']:
        print()
        __prnt = lambda k, v: print("{:>16}: {}".format(k, v))

        if template_data['ongoingMissionType'] == 'capture':
            mission = [m for m in template_data['pirateCaptureLevels']
                       if m['buildingLevel'] == template_data['ongoingMissionLevel']][0]

            __prnt("Ongoing mission:", decodeUnicodeEscape(mission['name']))
            __prnt("Capture points:", addThousandSeparator(mission['capturePoints']))
            __prnt("Gold:", addThousandSeparator(mission['gold']))
        else:
            # Other mission found. Probably raid.
            __prnt('Mission Type', template_data['ongoingMissionType'])

        __prnt("Time left:", daysHoursMinutes(template_data['ongoingMissionTimeRemaining']))

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
            {'key': 'distance', 'title': 'Distance', 'fmt': math.ceil},
        ],
        table_data=template_data['highscore'],
        row_colour=lambda row_id, row_data: (
            Colours.Text.Light.YELLOW if 'highscorePlayerPosition' in template_data
                                         and row_data is not None
                                         and row_id - 1 == template_data['highscorePlayerPosition']
            else Colours.Text.RESET),
        row_additional_indentation='  '
    )

    enter()
