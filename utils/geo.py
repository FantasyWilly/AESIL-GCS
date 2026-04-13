

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from core.state import GeoPoint

EARTH_RADIUS_M = 6_378_137.0


def distance_meters(point_a: GeoPoint, point_b: GeoPoint) -> float:
    lat1 = math.radians(point_a.latitude)
    lon1 = math.radians(point_a.longitude)
    lat2 = math.radians(point_b.latitude)
    lon2 = math.radians(point_b.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    sin_dlat = math.sin(dlat / 2.0)
    sin_dlon = math.sin(dlon / 2.0)
    a = sin_dlat ** 2 + math.cos(lat1) * math.cos(lat2) * sin_dlon ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(1.0 - a, 0.0)))
    return EARTH_RADIUS_M * c


@dataclass(slots=True)
class GeoProjector:
    reference: Optional[GeoPoint] = None

    def ensure_reference(self, point: GeoPoint) -> None:
        if self.reference is None:
            self.reference = point

    def to_local_xy(self, point: GeoPoint) -> Tuple[float, float]:
        self.ensure_reference(point)
        assert self.reference is not None

        lat0 = math.radians(self.reference.latitude)
        lon0 = math.radians(self.reference.longitude)
        lat = math.radians(point.latitude)
        lon = math.radians(point.longitude)

        x = (lon - lon0) * math.cos((lat + lat0) / 2.0) * EARTH_RADIUS_M
        y = (lat - lat0) * EARTH_RADIUS_M
        return x, y

    def bounds_for_points(
        self,
        points: Iterable[GeoPoint],
        padding_m: float = 50.0,
        minimum_span_m: float = 500.0,
    ) -> Tuple[float, float, float, float]:
        xy_points = [self.to_local_xy(point) for point in points]
        if not xy_points:
            half = minimum_span_m / 2.0
            return -half, half, -half, half

        xs = [xy[0] for xy in xy_points]
        ys = [xy[1] for xy in xy_points]

        min_x = min(xs) - padding_m
        max_x = max(xs) + padding_m
        min_y = min(ys) - padding_m
        max_y = max(ys) + padding_m

        span_x = max(max_x - min_x, minimum_span_m)
        span_y = max(max_y - min_y, minimum_span_m)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0

        return (
            center_x - span_x / 2.0,
            center_x + span_x / 2.0,
            center_y - span_y / 2.0,
            center_y + span_y / 2.0,
        )
