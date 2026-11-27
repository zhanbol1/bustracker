import json
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from transit.models import BusPosition
from transit.services import make_location_provider
from transit.services.location import DriverGPSProvider, MockProvider
from transit.services.tracking import BusTrackingService

from .base import Base

CENTER = (41.4300, 75.9950)


class TrackingBase(Base):
    def setUp(self):
        super().setUp()
        self.bus.driver = self.user
        self.bus.save()

    def age_last_position(self, seconds):
        BusPosition.objects.filter(bus=self.bus).update(recorded_at=timezone.now() - timedelta(seconds=seconds))


class BusTrackingServiceTests(TrackingBase):
    def test_driver_records_position(self):
        pos = BusTrackingService(self.user).record(self.bus, *CENTER)
        self.assertEqual((pos.lat, pos.lng), CENTER)
        self.assertEqual(self.bus.positions.count(), 1)

    def test_other_user_cannot_move_bus(self):
        with self.assertRaises(PermissionDenied):
            BusTrackingService(self.other).record(self.bus, *CENTER)

    def test_admin_is_not_the_driver_either(self):
        with self.assertRaises(PermissionDenied):
            BusTrackingService(self.admin).record(self.bus, *CENTER)

    def test_point_outside_city_rejected(self):
        with self.assertRaises(ValidationError):
            BusTrackingService(self.user).record(self.bus, 42.87, 74.59)  # Bishkek

    def test_normal_speed_accepted(self):
        BusTrackingService(self.user).record(self.bus, *CENTER)
        self.age_last_position(10)
        # ~100 m in 10 s is about 36 km/h
        BusTrackingService(self.user).record(self.bus, CENTER[0] + 0.0009, CENTER[1])
        self.assertEqual(self.bus.positions.count(), 2)

    def test_jump_faster_than_limit_rejected(self):
        BusTrackingService(self.user).record(self.bus, *CENTER)
        self.age_last_position(10)
        # ~1 km in 10 s is about 360 km/h
        with self.assertRaises(ValidationError):
            BusTrackingService(self.user).record(self.bus, CENTER[0] + 0.009, CENTER[1])
        self.assertEqual(self.bus.positions.count(), 1)


class PositionApiTests(TrackingBase):
    def post(self, body, client=None):
        url = reverse("api_bus_position", args=[self.bus.pk])
        data = body if isinstance(body, str) else json.dumps(body)
        return (client or self.client).post(url, data, content_type="application/json")

    def test_guest_gets_401(self):
        self.assertEqual(self.post({"lat": CENTER[0], "lng": CENTER[1]}).status_code, 401)

    def test_driver_gets_201_with_position(self):
        self.client.login(username="u1", password="pass12345")
        r = self.post({"lat": CENTER[0], "lng": CENTER[1]})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["plate"], "TEST1")
        self.assertIn("recorded_at", r.json())

    def test_not_the_driver_gets_403(self):
        self.client.login(username="u2", password="pass12345")
        r = self.post({"lat": CENTER[0], "lng": CENTER[1]})
        self.assertEqual(r.status_code, 403)
        self.assertIn("error", r.json())

    def test_outside_city_gets_400(self):
        self.client.login(username="u1", password="pass12345")
        self.assertEqual(self.post({"lat": 42.87, "lng": 74.59}).status_code, 400)

    def test_bad_json_gets_400(self):
        self.client.login(username="u1", password="pass12345")
        self.assertEqual(self.post("not json").status_code, 400)
        self.assertEqual(self.post({"lat": "x", "lng": 1}).status_code, 400)
        self.assertEqual(self.post([1, 2]).status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("api_bus_position", args=[self.bus.pk])).status_code, 405)

    def test_unknown_bus_gets_404(self):
        self.client.login(username="u1", password="pass12345")
        url = reverse("api_bus_position", args=[9999])
        self.assertEqual(self.client.post(url, "{}", content_type="application/json").status_code, 404)

    def test_csrf_token_required(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="u1", password="pass12345")
        self.assertEqual(self.post({"lat": CENTER[0], "lng": CENTER[1]}, client).status_code, 403)


class LocationSourceTests(Base):
    @override_settings(LOCATION_SOURCE="gps")
    def test_gps_setting_picks_driver_provider(self):
        self.assertIsInstance(make_location_provider(), DriverGPSProvider)

    @override_settings(LOCATION_SOURCE="mock")
    def test_mock_setting_picks_mock_provider(self):
        self.assertIsInstance(make_location_provider(), MockProvider)

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            make_location_provider("satellite")
