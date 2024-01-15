from ikabot.helpers.gui import addThousandSeparator, banner, bcolors, daysHoursMinutes, decodeUnicodeEscape, enter, \
    printTable
from ikabot.helpers.piracy import findCityWithTheBiggestPiracyFortress, \
    getPiracyTemplateData


def showPiracyInfo(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()

    great_pirate_city = findCityWithTheBiggestPiracyFortress(ikariam_service)
    template_data = getPiracyTemplateData(ikariam_service, great_pirate_city)

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
