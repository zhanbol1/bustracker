from django.conf import settings

from .eta import ETACalculator  # noqa: F401
from .location import DriverGPSProvider, LocationProvider, MockProvider  # noqa: F401
from .marks import MarkService  # noqa: F401
from .tracking import BusTrackingService  # noqa: F401

# Polymorphism: the map API only calls get_positions(); settings.LOCATION_SOURCE picks the class
PROVIDERS = {"mock": MockProvider, "gps": DriverGPSProvider}


def make_location_provider(source=None):
    source = source or settings.LOCATION_SOURCE
    if source not in PROVIDERS:
        raise ValueError(f"LOCATION_SOURCE must be one of {sorted(PROVIDERS)}, got {source!r}")
    return PROVIDERS[source]()


location_provider = make_location_provider()
