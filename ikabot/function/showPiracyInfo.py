from ikabot.helpers.pedirInfo import *
from ikabot.helpers.piracy import findCityWithTheBiggestPiracyFortress, \
  getPiracyTemplateData
from ikabot.helpers.varios import addThousandSeparator, daysHoursMinutes


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

        print(' Max fortress lvl:', template_data['buildingLevel'])
        print('      Crew points: {} ({} basic + {} own + {} bonus)'.format(
            addThousandSeparator(template_data['completeCrewPoints']),
            addThousandSeparator(template_data['basicCrewPoints']),
            addThousandSeparator(template_data['crewPoints']),
            addThousandSeparator(template_data['bonusCrewPoints']),
        ))

        print('   Capture points:', addThousandSeparator(template_data['capturePoints']))

        if template_data['hasOngoingMission']:
            mission = [m for m in template_data['pirateCaptureLevels']
                       if m['buildingLevel'] == template_data['ongoingMissionLevel']][0]
            print("   Ongoing mission: {} ({} time left)".format(
                decodeUnicodeEscape(mission['name']),
                daysHoursMinutes(template_data['ongoingMissionTimeRemaining'], include_seconds=True)
            ))

        if template_data['hasOngoingConvertion']:
            print('Ongoing conversion: {} points into {} crew strength ({} time left)'.format(
                addThousandSeparator(template_data['ongoingConvertionCapturePoints']),
                addThousandSeparator(template_data['ongoingConvertionCrewPoints']),
                daysHoursMinutes(template_data['ongoingConvertionTimeRemaining'], include_seconds=True)
            ))

        printTable(
            table_config=[
                {'key': 'place', 'title': 'Place'},
                {'key': 'name', 'title': 'Player', 'fmt': decodeUnicodeEscape},
                {'key': 'capturePoints', 'title': 'Capture Points', 'fmt': addThousandSeparator},
            ],
            table_data=template_data['highscore']
        )

        enter()
    except KeyboardInterrupt:
        print('Resetting')

    event.set()
