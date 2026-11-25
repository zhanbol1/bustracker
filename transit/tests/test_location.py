from datetime import timedelta

from django.utils import timezone

from transit.models import BusPosition
from transit.services.location import DriverGPSProvider, LocationProvider, MockProvider

from .base import Base


class LocationProviderTests(Base):
    def test_abstract_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            LocationProvider()

    def test_mock_position_is_on_route(self):
        loc = MockProvider(clock=lambda: 12345).get_position(self.bus)
        self.assertAlmostEqual(loc.lat, 41.4300, places=4)
        self.assertTrue(75.9700 <= loc.lng <= 75.9900)
        self.assertEqual(loc.source, "mock")

    def test_mock_bus_moves_over_time(self):
        a = MockProvider(clock=lambda: 0).get_position(self.bus)
        b = MockProvider(clock=lambda: 30).get_position(self.bus)
        self.assertNotEqual((a.lat, a.lng), (b.lat, b.lng))

    def test_inactive_bus_has_no_position(self):
        self.bus.is_active = False
        self.assertIsNone(MockProvider().get_position(self.bus))

    def test_gps_provider_offline_when_stale(self):
        p = BusPosition.objects.create(bus=self.bus, lat=41.43, lng=75.99)
        BusPosition.objects.filter(pk=p.pk).update(recorded_at=timezone.now() - timedelta(minutes=5))
        self.assertFalse(DriverGPSProvider().get_position(self.bus).online)
