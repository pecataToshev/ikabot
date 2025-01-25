import json
import logging
from typing import Union

from ikabot.config import actionRequest, city_url
from ikabot.helpers.buildings import find_city_with_the_biggest_building
from ikabot.helpers.getJson import parse_int
from ikabot.web.ikariamService import IkariamService


def getPiracyTemplateData(session, city_id):
    """
    Opens city and opens piracy screen. the returns the json
    :param session: ikabot.web.session.Session
    :param city_id: int
    :return: dict[]
    """
    session.post(city_url + str(city_id))
    html = session.post(params={
      'view': 'pirateFortress',
      'cityId': city_id,
      'position': 17,
      'backgroundView': 'city',
      'currentCityId': city_id,
      'actionRequest': actionRequest,
      'ajax': 1
    })

    _template_data = json.loads(html, strict=False)[2][1]
    _template_data = _template_data['load_js']['params']
    return json.loads(_template_data, strict=False)


def findCityWithTheBiggestPiracyFortress(ikariam_service: IkariamService) -> Union[dict, None]:
    """
    Finds and returns the id of the city with the biggest pirate fortress.
    :param ikariam_service: ikabot.web.session.Session
    :return: int
    """
    return find_city_with_the_biggest_building(ikariam_service, 'pirateFortress')


def convertCapturePoints(session, pirate_city_id, conversion_points):
    """Converts capture points into crew strength
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    pirate_city_id: int -> city id with a pirate fortress
    conversion_points: int/'all' -> how many points to convert
    :return bool: is successful
    """
    template_data = getPiracyTemplateData(session, pirate_city_id)
    captured_points = int(template_data['capturePoints'])

    if conversion_points == 'all':
        conversion_points = captured_points
    elif type(conversion_points) is str and conversion_points.startswith('over-'):
        minimum_threshold = parse_int(conversion_points.replace('over-', ''))
        conversion_points = max(0, captured_points - minimum_threshold)
    else:
        conversion_points = min(int(conversion_points), captured_points)

    if template_data['hasOngoingConvertion']:
        logging.info("Found ongoing conversion. Will will skip this one")
        return False

    if not isinstance(conversion_points, int):
        logging.error("Wrong value for conversion_points: %s (type: %s)", conversion_points, type(conversion_points))
        return False

    if conversion_points <= 0:
        logging.info("No points to convert")
        return False

    crew_strength = int(conversion_points / template_data['crewConversionFactor'])

    logging.info("Will start conversion of %d capture points into %d crew strength",
                 conversion_points, crew_strength)

    session.post(params={
      'action': 'PiracyScreen',
      'function': 'convert',
      'view': 'pirateFortress',
      'cityId': pirate_city_id,
      'activeTab': 'tabCrew',
      'crewPoints': str(crew_strength),
      'position': '17',
      'backgroundView': 'city',
      'currentCityId': pirate_city_id,
      'templateView': 'pirateFortress',
      'actionRequest': actionRequest,
      'ajax': '1'
    }, noIndex=True)

    return True
