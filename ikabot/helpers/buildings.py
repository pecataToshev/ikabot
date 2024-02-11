import json
from typing import Tuple, Union

from ikabot.config import actionRequest, city_url
from ikabot.helpers.citiesAndIslands import chooseCity
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import enter
from ikabot.web.ikariamService import IkariamService


def extract_target_building(city: dict, building_type: str):
    for building in city['position']:
        if building['building'] == building_type:
            return building
    return None


def get_building_info(ikariam_service: IkariamService, city_id: int, building: dict):
    data = ikariam_service.post(
        params={
            'view': building['building'],
            'cityId': city_id,
            'position': building['position'],
            'backgroundView': 'city',
            'currentCityId': city_id,
            'actionRequest': actionRequest,
            'ajax': '1'
        }
    )
    return json.loads(data, strict=False)


def choose_city_with_building(ikariam_service: IkariamService, building_type: str) \
        -> Union[None, Tuple[dict, dict, dict]]:

    print('Choose city with {}:'.format(building_type))
    city = chooseCity(ikariam_service)
    city = getCity(ikariam_service.get(city_url + city['id']))

    building = extract_target_building(city, building_type)
    if building is None:
        print('There is no {} in {}'.format(building_type, city['name']))
        enter()
        return None

    data = get_building_info(ikariam_service, city['id'], building)
    return city, building, data
