import unittest

from ikabot.helpers.satisfaction import get_satisfaction_level


class TestSatisfaction(unittest.TestCase):
    def test_get_satisfaction_level(self):
        satisfaction_classes = ["ecstatic", "happy", "neutral", "sad", "outraged"]
        class_values = [5, 4, 3, 2, 1]
        all_cases = [
            [6, 5.5, 5],
            [4.9, 4],
            [3.5, 3],
            [2.5, 2],
            [1.5, 1],
            [0.5, 0, -1]
        ]

        for cases, satisfaction_class in zip(all_cases, satisfaction_classes):
            for case in cases:
                self.assertEqual(get_satisfaction_level(satisfaction_classes, class_values, case), satisfaction_class)