from typing import Callable, Dict, List, Tuple


def search_additional_keys_in_dict(source, target):
    """
    Search for keys that were in source but are not in the target dictionary
    :param source: dict[dict]
    :param target: dict[dict]
    :return: list[int] ids of the additional keys in the source
    """
    return [k for k in source.keys() if k not in target]


def search_value_change_in_dict(
        dict_before: Dict[int, dict],
        dict_now: Dict[int, dict],
        state_getter: Callable[[dict], any]
) -> List[Tuple[dict, any, any]]:
    """
    Searches for change in state between two dicts of dicts with the state_getter function.
    Returns list of changes (new_dict, old_state, new_state)
    !!!IMPORTANT!!! old_state != new_state
    """
    _res = []
    for _id, _before in dict_before.items():
        _now = dict_now.get(_id, None)
        if _now is None:
            continue

        _state_before = state_getter(_before)
        _state_now = state_getter(_now)
        if _state_before != _state_now:
            _res.append((_now, _state_before, _state_now))

    return _res


def combine_dicts_with_lists(array_of_dicts: List[Dict[any, List[any]]]) -> Dict:
    combined_dict = {}
    for d in array_of_dicts:
        for key, value in d.items():
            if key in combined_dict:
                combined_dict[key].extend(value)
            else:
                combined_dict[key] = value
    return combined_dict
