import unittest

from ikabot import config
from ikabot.bot.transportGoodsBot import TransportJob
from ikabot.function.upgradeBuildingBotConfigurator import chooseResourceProviders

target = {'id': 1001, 'availableResources': [10, 11, 12, 13, 14], 'tradegood': 1, 'name': 'BeneficentCity'}
city_1 = {'id': 1002, 'availableResources': [15, 16, 17, 18, 19], 'tradegood': 1, 'name': 'City1'}
city_2 = {'id': 1003, 'availableResources': [00, 21, 22, 23, 24], 'tradegood': 2, 'name': 'City2'}
city_3 = {'id': 1004, 'availableResources': [25, 26, 00, 28, 29], 'tradegood': 3, 'name': 'City3'}
city_4 = {'id': 1005, 'availableResources': [30, 31, 32, 33, 34], 'tradegood': 4, 'name': 'City3'}
source_cities = [city_1, city_2, city_3, city_4]
all_cities = [target] + source_cities


def set_res(res, city, addition=0):
    r = [0] * len(city['availableResources'])
    r[res] = city['availableResources'][res] + addition
    return r


def calculate_missing(resource, cities_to_include):
    return sum([c['availableResources'][resource] for c in cities_to_include])


class TestChooseResourceProviders(unittest.TestCase):

    def test_choose_resource_providers_not_enough_resources(self):
        resource = 0
        resource_difference = 1
        cities_to_consider = [city_1, city_3, city_4]  # city 2 has no value, will be not considered and printed
        missing = resource_difference + calculate_missing(resource, cities_to_consider)
        config.predetermined_input = ['y'] * len(cities_to_consider) + ['n', 'y']

        enough_resources, send_resources, expand_anyway, routes \
            = chooseResourceProviders(all_cities, target, resource, missing, None, None)

        # Assert the expected return values
        self.assertFalse(enough_resources)
        self.assertFalse(send_resources)
        self.assertTrue(expand_anyway)
        self.assertIsInstance(routes, list)

        # Assert the expected TransportJob instances in the routes
        expected_routes = [
            TransportJob(city_1, target, set_res(resource, city_1)),
            TransportJob(city_3, target, set_res(resource, city_3)),
            TransportJob(city_4, target, set_res(resource, city_4)),
        ]

        self.assertEqual(routes, expected_routes)

    def test_choose_resource_providers_enough_resources(self,):
        resource = 1
        resource_difference = -5
        cities_to_consider = [city_1, city_2, city_3]
        missing = resource_difference + calculate_missing(resource, cities_to_consider)
        config.predetermined_input = ['y'] * len(cities_to_consider)

        enough_resources, send_resources, expand_anyway, routes \
            = chooseResourceProviders(all_cities, target, resource, missing, None, None)

        # Assert the expected return values
        self.assertTrue(enough_resources)
        self.assertIsNone(send_resources)
        self.assertIsNone(expand_anyway)
        self.assertIsInstance(routes, list)

        # Assert the expected TransportJob instances in the routes
        expected_routes = [
            TransportJob(city_1, target, set_res(resource, city_1)),
            TransportJob(city_2, target, set_res(resource, city_2)),
            TransportJob(city_3, target, set_res(resource, city_3, resource_difference)),
        ]

        self.assertEqual(routes, expected_routes)

    def test_choose_resource_providers_enough_resources_skip_city(self,):
        resource = 1
        resource_difference = -7
        cities_to_consider = [city_1, city_3]
        missing = resource_difference + calculate_missing(resource, cities_to_consider)
        config.predetermined_input = ['y', 'n', 'y']  # skip city_2

        enough_resources, send_resources, expand_anyway, routes \
            = chooseResourceProviders(all_cities, target, resource, missing, None, None)

        # Assert the expected return values
        self.assertTrue(enough_resources)
        self.assertIsNone(send_resources)
        self.assertIsNone(expand_anyway)
        self.assertIsInstance(routes, list)

        # Assert the expected TransportJob instances in the routes
        expected_routes = [
            TransportJob(city_1, target, set_res(resource, city_1)),
            TransportJob(city_3, target, set_res(resource, city_3, resource_difference)),
        ]

        self.assertEqual(routes, expected_routes)
