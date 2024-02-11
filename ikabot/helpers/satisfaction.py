from typing import List


def get_satisfaction_level(satisfaction_classes: List[str], class_values: List[int], satisfaction: float) -> str:
    for ind, sat_class in enumerate(satisfaction_classes):
        if class_values[ind] <= satisfaction:
            return satisfaction_classes[ind]
    return satisfaction_classes[-1]