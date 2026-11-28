import math

EARTH_RADIUS_M = 6_371_000


def distance_m(lat1, lng1, lat2, lng2):
    """Distance between two points in metres (haversine formula)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


class Polyline:
    """A route line. Encapsulates length calculation and finding a point at a given fraction of the way."""

    def __init__(self, points):
        if len(points) < 2:
            raise ValueError("Polyline needs at least 2 points")
        self.points = [(float(p[0]), float(p[1])) for p in points]
        self._segments = [
            distance_m(*self.points[i], *self.points[i + 1]) for i in range(len(self.points) - 1)
        ]

    @property
    def length_m(self):
        return sum(self._segments)

    def point_at(self, fraction):
        """Point on the line at the given fraction (0..1) of its length."""
        fraction = min(max(fraction, 0.0), 1.0)
        target = fraction * self.length_m
        walked = 0.0
        for i, seg in enumerate(self._segments):
            if walked + seg >= target or i == len(self._segments) - 1:
                t = 0 if seg == 0 else (target - walked) / seg
                (lat1, lng1), (lat2, lng2) = self.points[i], self.points[i + 1]
                return (lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t)
            walked += seg
        return self.points[-1]

    def locate(self, lat, lng):
        """Distance in metres along the line to the line's closest point to (lat, lng)."""
        best_gap, best_along, walked = None, 0.0, 0.0
        for i, seg in enumerate(self._segments):
            (lat1, lng1), (lat2, lng2) = self.points[i], self.points[i + 1]
            # flat projection is accurate enough inside one city
            kx = math.cos(math.radians(lat1))
            dx, dy = (lng2 - lng1) * kx, lat2 - lat1
            px, py = (lng - lng1) * kx, lat - lat1
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else min(max((px * dx + py * dy) / seg2, 0.0), 1.0)
            gap = distance_m(lat, lng, lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t)
            if best_gap is None or gap < best_gap:
                best_gap, best_along = gap, walked + t * seg
            walked += seg
        return best_along
