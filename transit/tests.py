from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Bus, BusPosition, Mark, MarkCategory, Route
from .services.geo import Polyline, distance_m
from .services.location import DriverGPSProvider, LocationProvider, MockProvider
from .services.marks import MarkService

PATH = [[41.4300, 75.9700], [41.4300, 75.9900]]


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pass12345")
        self.other = User.objects.create_user("u2", password="pass12345")
        self.admin = User.objects.create_user("adm", password="pass12345", is_staff=True)
        self.cat = MarkCategory.objects.create(name="Cafe", icon="☕")
        self.route = Route.objects.create(number="1", name="Test", path=PATH)
        self.bus = Bus.objects.create(route=self.route, plate="TEST1")

    def new_mark(self, lat=41.430, lng=75.990, **kw):
        return Mark(category=self.cat, title=kw.get("title", "Coffee"), lat=lat, lng=lng)


class GeoTests(TestCase):
    def test_distance(self):
        # ~1 degree of longitude at latitude 42.87 is about 81.6 km
        self.assertAlmostEqual(distance_m(42.87, 74.0, 42.87, 75.0) / 1000, 81.6, delta=0.5)

    def test_polyline_endpoints(self):
        line = Polyline(PATH)
        self.assertEqual(line.point_at(0), tuple(PATH[0]))
        self.assertAlmostEqual(line.point_at(1)[1], PATH[1][1])


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


class MarkRuleTests(Base):
    def test_create_valid_mark(self):
        mark = MarkService(self.user).create(self.new_mark())
        self.assertEqual(Mark.objects.get(pk=mark.pk).owner, self.user)

    def test_mark_outside_city_rejected(self):
        with self.assertRaises(ValidationError):
            MarkService(self.user).create(self.new_mark(lat=40.0, lng=70.0))

    def test_duplicate_nearby_rejected(self):
        MarkService(self.user).create(self.new_mark())
        with self.assertRaises(ValidationError):
            MarkService(self.user).create(self.new_mark(lat=41.43001, title="More coffee"))

    def test_daily_limit(self):
        for i in range(MarkService.DAILY_LIMIT):
            MarkService(self.user).create(self.new_mark(lat=41.40 + i * 0.002))
        with self.assertRaises(ValidationError):
            MarkService(self.user).create(self.new_mark(lat=41.45))

    def test_other_user_cannot_edit(self):
        mark = MarkService(self.user).create(self.new_mark())
        with self.assertRaises(PermissionDenied):
            MarkService(self.other).delete(mark)

    def test_admin_can_delete_any(self):
        mark = MarkService(self.user).create(self.new_mark())
        MarkService(self.admin).delete(mark)
        self.assertFalse(Mark.objects.exists())

    def test_route_needs_two_points(self):
        with self.assertRaises(ValidationError):
            Route(number="9", name="x", path=[[41.43, 75.99]]).full_clean()


class ViewTests(Base):
    def test_guest_sees_map_and_marks(self):
        self.assertEqual(self.client.get(reverse("map")).status_code, 200)
        self.assertEqual(self.client.get(reverse("api_marks")).status_code, 200)

    def test_guest_cannot_create_mark(self):
        r = self.client.get(reverse("mark_create"))
        self.assertRedirects(r, reverse("login") + "?next=" + reverse("mark_create"))

    def test_user_creates_mark_via_form(self):
        self.client.login(username="u1", password="pass12345")
        r = self.client.post(reverse("mark_create"),
                             {"title": "Coffee", "category": self.cat.id, "lat": 41.43, "lng": 75.99})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Mark.objects.count(), 1)

    def test_invalid_form_shows_errors(self):
        self.client.login(username="u1", password="pass12345")
        r = self.client.post(reverse("mark_create"), {"title": "", "category": self.cat.id})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)

    def test_regular_user_cannot_create_route(self):
        self.client.login(username="u1", password="pass12345")
        self.assertEqual(self.client.get(reverse("route_create")).status_code, 302)

    def test_admin_creates_route_with_stops(self):
        self.client.login(username="adm", password="pass12345")
        r = self.client.post(reverse("route_create"), {
            "number": "5", "name": "New", "color": "#ff0000", "is_active": "on",
            "path": '[[41.43,75.97],[41.43,75.99]]', "stops": '[{"name":"A","lat":41.43,"lng":75.97}]'})
        self.assertEqual(r.status_code, 302)
        route = Route.objects.get(number="5")
        self.assertEqual([s.name for s in route.ordered_stops()], ["A"])

    def test_route_search(self):
        Route.objects.create(number="42", name="Other", path=PATH)
        data = self.client.get(reverse("api_routes"), {"q": "42"}).json()["routes"]
        self.assertEqual([r["number"] for r in data], ["42"])

    def test_mark_search_empty_message(self):
        r = self.client.get(reverse("mark_list"), {"q": "nonexistent"})
        self.assertContains(r, "Nothing matches your search")

    def test_bus_api_returns_positions(self):
        data = self.client.get(reverse("api_route_buses", args=[self.route.pk])).json()
        self.assertEqual(data["buses"][0]["plate"], "TEST1")
