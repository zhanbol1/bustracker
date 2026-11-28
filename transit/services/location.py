"""Bus location sources.

Abstraction: LocationProvider defines the common get_position() interface.
Polymorphism: MockProvider and DriverGPSProvider answer the same call
differently, and the rest of the code (views, API) does not know which one is used.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from .geo import Polyline


@dataclass
class BusLocation:
    bus_id: int
    plate: str
    lat: float
    lng: float
    online: bool
    source: str

    def to_dict(self):
        return self.__dict__.copy()


class LocationProvider(ABC):
    source_name = "abstract"

    @abstractmethod
    def get_position(self, bus):
        """Return a BusLocation for the bus, or None if there is no position."""

    def is_moving_forward(self, bus):
        """True if the bus moves from the first point of its route line towards the last."""
        return True

    def get_positions(self, buses):
        result = []
        for bus in buses:
            loc = self.get_position(bus)
            if loc is not None:
                result.append(loc)
        return result


class MockProvider(LocationProvider):
    """Simulation: the bus drives back and forth along the route line at a constant speed."""

    source_name = "mock"

    def __init__(self, speed_kmh=25, clock=time.time):
        self.speed_ms = speed_kmh / 3.6
        self._clock = clock  # can be replaced in tests

    def _phase(self, bus, line):
        """0..0.5 = driving forward along the line, 0.5..1 = driving back."""
        cycle_s = 2 * line.length_m / self.speed_ms  # there and back
        return (self._clock() / cycle_s + bus.mock_offset) % 1.0

    def is_moving_forward(self, bus):
        return len(bus.route.path) < 2 or self._phase(bus, Polyline(bus.route.path)) < 0.5

    def get_position(self, bus):
        if not bus.is_active or len(bus.route.path) < 2:
            return None
        line = Polyline(bus.route.path)
        phase = self._phase(bus, line)
        fraction = phase * 2 if phase < 0.5 else 2 - phase * 2
        lat, lng = line.point_at(fraction)
        return BusLocation(bus.id, bus.plate, lat, lng, online=True, source=self.source_name)


class DriverGPSProvider(LocationProvider):
    """Real data: the last position sent by the driver's phone."""

    source_name = "gps"
    OFFLINE_AFTER = timedelta(minutes=2)

    def get_position(self, bus):
        last = bus.positions.first()
        if last is None:
            return None
        online = timezone.now() - last.recorded_at <= self.OFFLINE_AFTER
        return BusLocation(bus.id, bus.plate, last.lat, last.lng, online, self.source_name)

    def is_moving_forward(self, bus):
        last_two = list(bus.positions.all()[:2])
        if len(last_two) < 2 or len(bus.route.path) < 2:
            return True
        line = Polyline(bus.route.path)
        newer, older = (line.locate(p.lat, p.lng) for p in last_two)
        return newer >= older
