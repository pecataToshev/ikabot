import unittest

from ikabot.helpers.dicts import combine_dicts_with_lists, search_additional_keys_in_dict, search_value_change_in_dict_for_presented_values_in_now


class TestSearchAdditionalKeysInDict(unittest.TestCase):
    def test_no_additional_keys(self):
        source = {'a': 1, 'b': 2}
        target = {'a': 1, 'b': 2}
        self.assertEqual(search_additional_keys_in_dict(source, target), [])

    def test_additional_keys_present(self):
        source = {'a': 1, 'b': 2, 'c': 3}
        target = {'a': 1, 'b': 2}
        self.assertEqual(search_additional_keys_in_dict(source, target), ['c'])

    def test_empty_source_dict(self):
        source = {}
        target = {'a': 1, 'b': 2}
        self.assertEqual(search_additional_keys_in_dict(source, target), [])

    def test_empty_target_dict(self):
        source = {'a': 1, 'b': 2}
        target = {}
        self.assertEqual(search_additional_keys_in_dict(source, target), ['a', 'b'])


class TestSearchValueChangeInDict(unittest.TestCase):

    def test_search_value_change_in_dict_no_changes(self):
        dict_before = {1: {'a': 1, 'b': 2}, 2: {'c': 3}}
        dict_now = {1: {'a': 1, 'b': 2}, 2: {'c': 3}}
        result = search_value_change_in_dict_for_presented_values_in_now(dict_before, dict_now, lambda x: x.get('c', None))
        self.assertEqual(result, [])

    def test_search_value_change_in_dict_with_changes(self):
        dict_before = {1: {'a': 1, 'b': 2, 'c': 3}, 2: {'c': 3}}
        dict_now = {1: {'a': 1, 'b': 3, 'c': 400}, 2: {'c': 3}}
        result = search_value_change_in_dict_for_presented_values_in_now(dict_before, dict_now, lambda x: x.get('c', None))
        expected_result = [({'a': 1, 'b': 3, 'c': 400}, 3, 400)]
        self.assertEqual(result, expected_result)

    def test_search_value_change_in_dict_with_missing_keys(self):
        dict_before = {1: {'a': 1, 'b': 2}, 2: {'c': 3}}
        dict_now = {1: {'a': 1}, 3: {'d': 4}}
        result = search_value_change_in_dict_for_presented_values_in_now(dict_before, dict_now, lambda x: x.get('c', None))
        self.assertEqual(result, [])
        # the above test case is expected because if the city is missing in the now_dict,
        # it should be caught in other part of the code (with the disappearing data)

        dict_before = {1: {'a': 1}, 3: {'d': 4}}
        dict_now = {1: {'a': 1, 'b': 2}, 2: {'c': 3}}
        result = search_value_change_in_dict_for_presented_values_in_now(dict_before, dict_now, lambda x: x.get('c', None))
        self.assertEqual(result, [({'c': 3}, None, 3)])


class TestCombineDictsWithLists(unittest.TestCase):

    def test_combine_dicts_with_lists(self):
        array_of_dicts = [
            {'a': [1, 2], 'b': [3]},
            {'b': [4, 5], 'c': [6]}
        ]
        self.assertEqual(combine_dicts_with_lists(array_of_dicts),
                         {'a': [1, 2], 'b': [3, 4, 5], 'c': [6]})

        array_of_dicts = [
            {'a': [1, 2], 'b': [3]},
            {'b': [4, 5], 'c': [6]},
            {'d': [7]}
        ]
        self.assertEqual(combine_dicts_with_lists(array_of_dicts),
                         {'a': [1, 2], 'b': [3, 4, 5], 'c': [6], 'd': [7]})

        array_of_dicts = [
            {'a': [1, 2], 'b': [3]},
            {'b': [4, 5], 'c': [6]},
            {'c': [7, 8]}
        ]
        self.assertEqual(combine_dicts_with_lists(array_of_dicts),
                         {'a': [1, 2], 'b': [3, 4, 5], 'c': [6, 7, 8]})

        array_of_dicts = [
            {'a': [1, 2], 'b': [3]},
            {'b': [4, 5], 'c': [6]},
            {'d': [7]},
            {'e': [8, 9]}
        ]
        self.assertEqual(combine_dicts_with_lists(array_of_dicts),
                         {'a': [1, 2], 'b': [3, 4, 5], 'c': [6], 'd': [7], 'e': [8, 9]})

