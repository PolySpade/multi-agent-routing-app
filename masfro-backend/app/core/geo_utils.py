# filename: app/core/geo_utils.py

"""
Shared geographic utilities for MAS-FRO.

Provides haversine distance calculation used by multiple modules
(risk_aware_astar, hazard_agent, etc.).
"""

import math
from typing import Tuple


def haversine_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calculate the great circle distance between two points on Earth.

    Uses the Haversine formula to compute the distance between two
    geographic coordinates.

    Args:
        coord1: First coordinate (latitude, longitude) in degrees
        coord2: Second coordinate (latitude, longitude) in degrees

    Returns:
        Distance in meters
    """
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in meters
    radius = 6371000

    return radius * c
