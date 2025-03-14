import math


def el(elevation):
    """
    Round an elevation value to 3 decimal places.

    Args:
        elevation (float): The elevation value to round

    Returns:
        float: The rounded elevation value
    """
    return round(elevation, 3)


def string_to_coor(string):
    """
    Convert a string representation of coordinates to a list of floats.

    Args:
        string (str): String in format "x__y__z"

    Returns:
        list: List of coordinates [x, y, z] as floats
    """
    try:
        return [float(num) for num in string.split("__")]
    except ValueError:
        raise ValueError(
            f"Invalid coordinate string format: {string}. Expected format: 'x__y__z'"
        )
