import unittest

from ikabot.__main__ import init_parameters


class TestInitParameters(unittest.TestCase):
    def test_init_parameters_with_values(self):
        input_args = [
            "--option=value",
            "--name=John",
            "--age=25",
            "--gender=male",
            "--disablePrinting",
            "5",
            "otherInput",
            "wq",
            "--isTrue=true",
            "--isFalse=false",
            "--isOn=On",
            "--isOff=off",
            "--isTrueNoValue",
            "--dbFile=~/.ikabot.db",
            "--valueWithStrangeCharacters=\\ala-bala/*.-+@#$%^&*(){}[]|<>?~`"
        ]
        result_dict, other_values = init_parameters(input_args)

        expected_dict = {
            'option': 'value',
            'name': 'John',
            'age': 25,
            'gender': 'male',
            'disablePrinting': True,
            'isTrue': True,
            'isFalse': False,
            'isOn': True,
            'isOff': False,
            'isTrueNoValue': True,
            'dbFile': '~/.ikabot.db',
            'valueWithStrangeCharacters': '\\ala-bala/*.-+@#$%^&*(){}[]|<>?~`'
        }
        expected_other_values = [5, 'otherInput', 'wq']

        self.assertEqual(result_dict, expected_dict)
        self.assertEqual(other_values, expected_other_values)

    def test_init_parameters_empty_input(self):
        result_dict, other_values = init_parameters([])

        self.assertEqual(result_dict, {})
        self.assertEqual(other_values, [])

    def test_init_parameters_only_values(self):
        input_args = ["1", "value2", "true", 'off']
        result_dict, other_values = init_parameters(input_args)

        self.assertEqual(result_dict, {})
        self.assertEqual(other_values, [1, 'value2', True, False])

    def test_init_parameters_only_dict_input(self):
        input_args = ["--option=value", "--name=John", "--age=25"]
        result_dict, other_values = init_parameters(input_args)

        expected_dict = {
            'option': 'value',
            'name': 'John',
            'age': 25
        }

        self.assertEqual(result_dict, expected_dict)
        self.assertEqual(other_values, [])
