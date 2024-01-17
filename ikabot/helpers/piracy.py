import json
import logging

from ikabot.config import city_url, actionRequest
from ikabot.helpers.getJson import getCity
from ikabot.helpers.citiesAndIslands import getIdsOfCities


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


def findCityWithTheBiggestPiracyFortress(ikariam_service):
    """
    Finds and returns the id of the city with the biggest pirate fortress.
    :param ikariam_service: ikabot.web.session.Session
    :return: int
    """
    [cities_ids, _] = getIdsOfCities(ikariam_service)
    pirate_city = None
    max_level = 0
    for city_id in cities_ids:
        city = getCity(ikariam_service.get(city_url + city_id))
        for building in city['position']:
            if building['building'] == 'pirateFortress' and building['level'] > max_level:
                pirate_city = city_id
                max_level = building['level']

    return pirate_city


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
    else:
        conversion_points = min(int(conversion_points), captured_points)

    if template_data['hasOngoingConvertion']:
        logging.info("Found ongoing conversion. Will will skip this one")
        return False

    if conversion_points == 0:
        logging.info("No points to convert")
        return False

    crew_strength = int(conversion_points / template_data['crewConversionFactor'])

    logging.info("Will start conversion of %d capture points into %d crew strenght",
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
