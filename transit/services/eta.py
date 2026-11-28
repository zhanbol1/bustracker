"""Arrival times: how long until each bus of a route reaches a stop."""

from dataclasses import dataclass

from .geo import Polyline


@dataclass
class Arrival:
    bus_id: int
    plate: str
    distance_m: int
    eta_s: int

    def to_dict(self):
        return {**self.__dict__, "eta_min": round(self.eta_s / 60)}


class ETACalculator:
    """Distance along the route line from each bus to the stop, divided by an average speed.

    Buses drive to the end of the line and come back, so a stop behind the bus is reached
    after the turn-around.
    """

    AVERAGE_SPEED_KMH = 20  # city average including stops

    def __init__(self, route, provider, speed_kmh=None):
        self.route = route
        self.line = Polyline(route.path)
        self.provider = provider
        self.speed_ms = (speed_kmh or self.AVERAGE_SPEED_KMH) / 3.6

    def distance_to(self, bus_along, stop_along, forward=True):
        """Metres the bus still drives to reach the stop (both given as distance along the line)."""
        length = self.line.length_m
        if forward:
            if stop_along >= bus_along:
                return stop_along - bus_along
            return (length - bus_along) + (length - stop_along)
        if stop_along <= bus_along:
            return bus_along - stop_along
        return bus_along + stop_along

    def arrivals(self, stop):
        """Arrivals of online buses at the stop, soonest first."""
        stop_along = self.line.locate(stop.lat, stop.lng)
        result = []
        for bus in self.route.buses.filter(is_active=True).select_related("route"):
            loc = self.provider.get_position(bus)
            if loc is None or not loc.online:
                continue
            bus_along = self.line.locate(loc.lat, loc.lng)
            meters = self.distance_to(bus_along, stop_along, self.provider.is_moving_forward(bus))
            result.append(Arrival(bus.id, bus.plate, round(meters), round(meters / self.speed_ms)))
        return sorted(result, key=lambda a: a.eta_s)
