"""Business rules for positions sent by a driver's phone. The API calls BusTrackingService."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from ..models import BusPosition, validate_in_city
from .geo import distance_m


class BusTrackingService:
    MAX_SPEED_KMH = 120  # rule 3: faster than this since the last point means a GPS glitch

    def __init__(self, user):
        self.user = user

    def _check_driver(self, bus):
        # rule 1: only the driver assigned to this bus may move it
        if not self.user.is_authenticated or bus.driver_id != self.user.id:
            raise PermissionDenied("Only the driver of this bus can send its position.")

    def _check_speed(self, bus, lat, lng, now):
        last = bus.positions.first()
        if last is None:
            return
        seconds = max((now - last.recorded_at).total_seconds(), 1.0)
        speed_kmh = distance_m(last.lat, last.lng, lat, lng) / seconds * 3.6
        if speed_kmh > self.MAX_SPEED_KMH:
            raise ValidationError(
                f"Position jumped too far: {speed_kmh:.0f} km/h since the last point "
                f"(limit {self.MAX_SPEED_KMH} km/h)."
            )

    def record(self, bus, lat, lng):
        """Check the rules and store the position. Raises PermissionDenied or ValidationError."""
        self._check_driver(bus)
        validate_in_city(lat, lng)  # rule 2: the point is inside the city
        self._check_speed(bus, lat, lng, timezone.now())
        return BusPosition.objects.create(bus=bus, lat=lat, lng=lng)
