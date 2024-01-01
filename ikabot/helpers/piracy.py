import json

from ikabot.config import city_url, actionRequest
from ikabot.helpers.getJson import getCity
from ikabot.helpers.pedirInfo import getIdsOfCities
from ikabot.helpers.varios import decodeUnicodeEscape


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

    return json.loads(decodeUnicodeEscape(html), strict=False)[2][1]


def findCityWithTheBiggestPiracyFortress(session):
    """
    Finds and returns the id of the city with the biggest pirate fortress.
    :param session: ikabot.web.session.Session
    :return: int
    """
    [cities_ids, _] = getIdsOfCities(session)
    pirate_city = None
    max_level = 0
    for city_id in cities_ids:
        city = getCity(session.get(city_url + city_id))
        for building in city['position']:
            if building['building'] == 'pirateFortress' and building['level'] > max_level:
                pirate_city = city_id
                max_level = building['level']

    return pirate_city