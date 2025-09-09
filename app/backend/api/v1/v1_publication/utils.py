from .constants import DroughtCategory


def get_category(value: float):
    value = round(value, 3)
    if (value < 0):
        return DroughtCategory.none
    if (value >= 0 and value <= 0.02):
        return DroughtCategory.d4
    if (value > 0.02 and value <= 0.05):
        return DroughtCategory.d3
    if (value > 0.05 and value <= 0.1):
        return DroughtCategory.d2
    if (value > 0.1 and value <= 0.2):
        return DroughtCategory.d1
    if (value > 0.2 and value <= 0.3):
        return DroughtCategory.d0
    return DroughtCategory.normal
