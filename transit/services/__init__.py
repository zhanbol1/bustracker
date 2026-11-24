from .location import DriverGPSProvider, LocationProvider, MockProvider  # noqa: F401
from .marks import MarkService  # noqa: F401

# Which position source the site uses. To switch to real GPS,
# change this line to DriverGPSProvider().
location_provider = MockProvider()
