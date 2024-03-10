import unittest

from ikabot.helpers.gui import daysHoursMinutes


class TestDaysHoursMinutes(unittest.TestCase):

    def test_zero_seconds(self):
        self.assertEqual(daysHoursMinutes(0), '0S')

    def test_seconds_only(self):
        self.assertEqual(daysHoursMinutes(45), '45S')

    def test_minutes_only(self):
        self.assertEqual(daysHoursMinutes(130), '2M 10S')

    def test_hours_only(self):
        self.assertEqual(daysHoursMinutes(7200), '2H')

    def test_days_and_hours(self):
        self.assertEqual(daysHoursMinutes(100000), '1D 3H')

    def test_force_include_smaller_unit_true(self):
        self.assertEqual(daysHoursMinutes(65, True), '1M 5S')
        self.assertEqual(daysHoursMinutes(65, True, True), '1M 05S')

    def test_force_include_smaller_unit_false(self):
        self.assertEqual(daysHoursMinutes(60), '1M')
        self.assertEqual(daysHoursMinutes(60, True), '1M 0S')
        self.assertEqual(daysHoursMinutes(60, True, True), '1M 00S')

    def test_large_duration_without_hour(self):
        _seconds = 3456789
        self.assertEqual(daysHoursMinutes(_seconds), '40D')  # by default, we don't include smaller units than hours
        self.assertEqual(daysHoursMinutes(_seconds, True), '40D 0H 13M 9S')
        self.assertEqual(daysHoursMinutes(_seconds, True, True), '40D 00H 13M 09S')

    def test_large_duration_with_hour(self):
        _seconds = 3460389
        self.assertEqual(daysHoursMinutes(_seconds), '40D 1H')
        self.assertEqual(daysHoursMinutes(_seconds, add_leading_zeroes_on_smaller_unit=True), '40D 01H')
        self.assertEqual(daysHoursMinutes(_seconds, True), '40D 1H 13M 9S')
        self.assertEqual(daysHoursMinutes(_seconds, True, True), '40D 01H 13M 09S')
        self.assertEqual(daysHoursMinutes(_seconds, add_leading_zeroes_on_smaller_unit=True), '40D 01H')
