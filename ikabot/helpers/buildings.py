import json
from enum import Enum
from typing import Tuple, Union

from ikabot.config import actionRequest, city_url
from ikabot.helpers.citiesAndIslands import getCityWithCache, getIdsOfCities
from ikabot.helpers.gui import decodeUnicodeEscape, enter
from ikabot.helpers.userInput import read
from ikabot.web.ikariamService import IkariamService


class BuildingTypes(Enum):
    TOWN_HALL = {'building': 'townHall'}
    ACADEMY = {'building': 'academy'}
    WAREHOUSE = {'building': 'warehouse'}
    TAVERN = {'building': 'tavern'}
    PALACE = {'building': 'palace'}
    PALACE_COLONY = {'building': 'palaceColony'}
    MUSEUM = {'building': 'museum'}
    PORT = {'building': 'port'}
    SHIPYARD = {'building': 'shipyard'}
    BARRACKS = {'building': 'barracks'}
    WALL = {'building': 'wall'}
    EMBASSY = {'building': 'embassy'}
    BRANCH_OFFICE = {'building': 'branchOffice'}
    WORKSHOP = {'building': 'workshop'}
    SAFE_HOUSE = {'building': 'safehouse'}

    FORESTER = {'building': 'forester'}
    GLASSBLOWING = {'building': 'glassblowing'}
    ALCHEMIST = {'building': 'alchemist'}
    WINEGROWER = {'building': 'winegrower'}
    STONEMASON = {'building': 'stonemason'}
    CARPENTERING = {'building': 'carpentering', 'reducesResources': 'wood'}
    OPTICIAN = {'building': 'optician', 'reducesResources': 'crystal'}
    FIRE_WORKER = {'building': 'fireworker', 'reducesResources': 'sulphur'}
    VINEYARD = {'building': 'vineyard', 'reducesResources': 'wine'}
    ARCHITECT = {'building': 'architect', 'reducesResources': 'stone'}
    TEMPLE = {'building': 'temple'}
    DUMPER = {'building': 'dump'}
    PIRATE_FORTRESS = {'building': 'pirateFortress'}
    BLACK_MARKET = {'building': 'blackMarket'}
    MARINE_CHART_ARCHIVE = {'building': 'marineChartArchive'}

    DOCKYARD = {'building': 'dockyards'}
    SHRINE = {'building': 'shrineOfOlympus'}


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
    """
    Prompts the user to select from cities that have the specified building type.
    Only shows cities with the building, not all cities.
    Uses cached city data (valid for 5 minutes) to reduce HTTP requests.
    
    Parameters
    ----------
    ikariam_service : IkariamService
        Session object
    building_type : str
        The building type to filter by (e.g., 'workshop', 'barracks', 'academy')
    
    Returns
    -------
    tuple or None
        (city, building, data) tuple for the selected city, or None if no cities have the building
    """
    # Get all cities and filter to only those with the specified building
    (ids, cities) = getIdsOfCities(ikariam_service)
    cities_with_building = []
    
    print('Loading cities', end='', flush=True)
    for city_id in ids:
        # Use cached city data to reduce requests
        city = getCityWithCache(ikariam_service, city_id, show_progress=True)
        building = extract_target_building(city, building_type)
        if building is not None:
            cities_with_building.append((city, building))
    print(' Done!')
    print()
    
    if len(cities_with_building) == 0:
        print('No {} found in any city!'.format(building_type))
        enter()
        return None
    
    # Let user select from cities with the building
    print('Select city with {}:\n'.format(building_type))
    for idx, (city, building) in enumerate(cities_with_building, 1):
        print('({}) {} - {} Level {}'.format(
            idx, 
            decodeUnicodeEscape(city['name']), 
            building_type.capitalize(),
            building['level']
        ))
    
    selection = read(min=1, max=len(cities_with_building), digit=True)
    city, building = cities_with_building[selection - 1]
    
    # Get building data
    data = get_building_info(ikariam_service, city['id'], building)
    return city, building, data


def find_city_with_the_biggest_building(ikariam_service: IkariamService, building_type: str, show_progress: bool = False) -> Union[dict, None]:
    """
    Finds and returns the city with the highest building level of given type.
    Uses cached city data (valid for 5 minutes) to reduce HTTP requests.
    
    Parameters
    ----------
    ikariam_service : IkariamService
        Session object
    building_type : str
        The building type to search for
    show_progress : bool
        Whether to show progress dots while loading (default: False)
    """
    [cities_ids, _] = getIdsOfCities(ikariam_service)
    great_city = None
    max_level = 0
    
    if show_progress:
        print('Searching cities', end='', flush=True)
    
    for city_id in cities_ids:
        # Use cached city data to reduce requests
        city = getCityWithCache(ikariam_service, city_id, show_progress=show_progress)
        for building in city['position']:
            if building['building'] == building_type and building['level'] > max_level:
                great_city = city
                max_level = building['level']
    
    if show_progress:
        print(' Done!')

    return great_city
