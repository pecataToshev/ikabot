import unittest

from ikabot.bot.islandMonitoringBot import CityStatusUpdate, IslandMonitoringBot


class IslandMonitoringBot_TestMonitorLevelUp(unittest.TestCase):
    def test_monitor_level_up_colony_level_up(self):
        # Create test data for colony level up
        cities_before = {1: {'level': 1}, 2: {'level': 0}}
        cities_now = {1: {'level': 2}, 2: {'level': 0}}

        # Call the method
        result = IslandMonitoringBot.monitor_level_up(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.COLONY_LEVEL_UP]}
        self.assertEqual(result, expected_result)

    def test_monitor_level_up_no_level_change(self):
        # Create test data where no level changes occur
        cities_before = {1: {'level': 1}, 2: {'level': 0}}
        cities_now = {1: {'level': 1}, 2: {'level': 0}}

        # Call the method
        result = IslandMonitoringBot.monitor_level_up(cities_before, cities_now)

        # Assert the expected result
        self.assertEqual(result, {})

    def test_monitor_level_up_colony_started_initializing(self):
        # Create test data where a new colony is initialized
        cities_before = {}
        cities_now = {1: {'level': 0}}

        # Call the method
        result = IslandMonitoringBot.monitor_level_up(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.COLONY_STARTED_INITIALIZING]}
        self.assertEqual(result, expected_result)

    def test_monitor_level_up_colony_initialized(self):
        # Create test data where a colony is initialized
        cities_before = {1: {'level': 0}}
        cities_now = {1: {'level': 1}}

        # Call the method
        result = IslandMonitoringBot.monitor_level_up(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.COLONY_INITIALIZED]}
        self.assertEqual(result, expected_result)

    def test_monitor_level_up_colony_initialized_from_none(self):
        # Create test data where a colony is initialized
        cities_before = {}
        cities_now = {1: {'level': 3}}

        # Call the method
        result = IslandMonitoringBot.monitor_level_up(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.COLONY_INITIALIZED]}
        self.assertEqual(result, expected_result)


class IslandMonitoringBot_TestMonitorStatusChange(unittest.TestCase):
    def test_monitor_status_change_vacation_returned(self):
        # Create test data for city returning from vacation
        cities_before = {1: {'id': 1, 'state': 'vacation'}, 2: {'id': 2, 'state': 'active'}}
        cities_now = {1: {'id': 1, 'state': 'active'}, 2: {'id': 2, 'state': 'active'}}

        # Call the method
        result = IslandMonitoringBot.monitor_status_change(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.VACATION_RETURNED]}
        self.assertEqual(result, expected_result)

    def test_monitor_status_change_vacation_went(self):
        # Create test data for city going on vacation
        cities_before = {1: {'id': 1, 'state': 'active'}, 2: {'id': 2, 'state': 'inactive'}}
        cities_now = {1: {'id': 1, 'state': 'vacation'}, 2: {'id': 2, 'state': 'inactive'}}

        # Call the method
        result = IslandMonitoringBot.monitor_status_change(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.VACATION_WENT]}
        self.assertEqual(result, expected_result)

    def test_monitor_status_change_re_activated(self):
        # Create test data for city re-activation
        cities_before = {1: {'id': 1, 'state': 'inactive'}, 2: {'id': 2, 'state': 'active'}}
        cities_now = {1: {'id': 1, 'state': 'active'}, 2: {'id': 2, 'state': 'active'}}

        # Call the method
        result = IslandMonitoringBot.monitor_status_change(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.RE_ACTIVATED]}
        self.assertEqual(result, expected_result)

    def test_monitor_status_change_inactivated(self):
        # Create test data for city inactivation
        cities_before = {1: {'id': 1, 'state': 'active'}, 2: {'id': 2, 'state': 'active'}}
        cities_now = {1: {'id': 1, 'state': 'inactive'}, 2: {'id': 2, 'state': 'active'}}

        # Call the method
        result = IslandMonitoringBot.monitor_status_change(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.INACTIVATED]}
        self.assertEqual(result, expected_result)


class IslandMonitoringBot_TestMonitorFights(unittest.TestCase):
    def test_monitor_fights_fight_started(self):
        # Create test data for starting a fight
        cities_before = {1: {'id': 1}, 2: {'id': 2, 'infos': {'armyAction': 'idle'}}}
        cities_now = {1: {'id': 1, 'infos': {'armyAction': 'fight'}}, 2: {'id': 2, 'infos': {'armyAction': 'idle'}}}

        # Call the method
        result = IslandMonitoringBot.monitor_fights(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.FIGHT_STARTED]}
        self.assertEqual(result, expected_result)

    def test_monitor_fights_fight_stopped(self):
        # Create test data for stopping a fight
        cities_before = {1: {'id': 1, 'infos': {'armyAction': 'fight'}}, 2: {'id': 2, 'infos': {'armyAction': 'idle'}}}
        cities_now = {1: {'id': 1}, 2: {'id': 2, 'infos': {'armyAction': 'idle'}}}

        # Call the method
        result = IslandMonitoringBot.monitor_fights(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.FIGHT_STOPPED]}
        self.assertEqual(result, expected_result)


class IslandMonitoringBot_TestMonitorPiracy(unittest.TestCase):
    def test_monitor_piracy_piracy_created(self):
        # Create test data for piracy created
        cities_before = {1: {'id': 1, 'actions': {'piracy_raid': 0}}, 2: {'id': 2, 'actions': {'piracy_raid': 1}}}
        cities_now = {1: {'id': 1, 'actions': {'piracy_raid': 1}}, 2: {'id': 2, 'actions': {'piracy_raid': 1}}}

        # Call the method
        result = IslandMonitoringBot.monitor_piracy(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.PIRACY_CREATED]}
        self.assertEqual(result, expected_result)

    def test_monitor_piracy_piracy_removed(self):
        # Create test data for piracy removed
        cities_before = {1: {'id': 1, 'actions': {'piracy_raid': 1}}, 2: {'id': 2, 'actions': {'piracy_raid': 1}}}
        cities_now = {1: {'id': 1, 'actions': {'piracy_raid': 0}}, 2: {'id': 2, 'actions': {'piracy_raid': 1}}}

        # Call the method
        result = IslandMonitoringBot.monitor_piracy(cities_before, cities_now)

        # Assert the expected result
        expected_result = {1: [CityStatusUpdate.PIRACY_REMOVED]}
        self.assertEqual(result, expected_result)
