from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from transit.models import Bus, BusPosition, Route
from transit.services.eta import ETACalculator
from transit.services.geo import Polyline
from transit.services.location import DriverGPSProvider, MockProvider
from transit.services.routes import RouteService

from .base import Base

# Straight west-east line through the city, about 1.67 km long
LINE = [[41.4300, 75.9700], [41.4300, 75.9900]]
WEST, MIDDLE, EAST = (41.4300, 75.9700), (41.4300, 75.9800), (41.4300, 75.9900)


class FixedProvider(MockProvider):
    """Bus at a given point, moving in a given direction."""

    def __init__(self, point, forward=True, online=True):
        super().__init__()
        self.point, self.forward, self.online = point, forward, online

    def get_position(self, bus):
        loc = super().get_position(bus)
        loc.lat, loc.lng = self.point
        loc.online = self.online
        return loc

    def is_moving_forward(self, bus):
        return self.forward


class PolylineLocateTests(Base):
    def test_point_on_line(self):
        line = Polyline(LINE)
        self.assertAlmostEqual(line.locate(*MIDDLE), line.length_m / 2, delta=1)

    def test_point_beside_line_projects_onto_it(self):
        line = Polyline(LINE)
        self.assertAlmostEqual(line.locate(41.4310, 75.9800), line.length_m / 2, delta=1)

    def test_point_past_the_end_clamps(self):
        line = Polyline(LINE)
        self.assertAlmostEqual(line.locate(41.4300, 76.0000), line.length_m, delta=1)
        self.assertAlmostEqual(line.locate(41.4300, 75.9600), 0, delta=1)

    def test_multi_segment_line(self):
        line = Polyline([[41.43, 75.97], [41.43, 75.98], [41.44, 75.98]])
        first_leg = line._segments[0]
        self.assertAlmostEqual(line.locate(41.435, 75.98), first_leg + line._segments[1] / 2, delta=1)


class ETACalculatorTests(Base):
    def setUp(self):
        super().setUp()
        self.route = Route.objects.create(number="9", name="Line", path=LINE)
        RouteService.save(self.route, [
            {"name": "West", "lat": WEST[0], "lng": WEST[1]},
            {"name": "East", "lat": EAST[0], "lng": EAST[1]},
        ])
        self.west, self.east = self.route.ordered_stops()
        self.bus = Bus.objects.create(route=self.route, plate="ETA1")
        self.half = Polyline(LINE).length_m / 2

    def arrivals(self, provider, stop, speed=None):
        return ETACalculator(self.route, provider, speed).arrivals(stop)

    def test_stop_ahead(self):
        a = self.arrivals(FixedProvider(MIDDLE, forward=True), self.east)[0]
        self.assertAlmostEqual(a.distance_m, self.half, delta=2)

    def test_stop_behind_goes_round_the_end(self):
        # driving east from the middle: to the east end (half) and all the way back (full)
        a = self.arrivals(FixedProvider(MIDDLE, forward=True), self.west)[0]
        self.assertAlmostEqual(a.distance_m, 3 * self.half, delta=3)

    def test_driving_back(self):
        a = self.arrivals(FixedProvider(MIDDLE, forward=False), self.west)[0]
        self.assertAlmostEqual(a.distance_m, self.half, delta=2)

    def test_eta_is_distance_over_speed(self):
        a = self.arrivals(FixedProvider(MIDDLE), self.east, speed=36)[0]  # 36 km/h = 10 m/s
        self.assertAlmostEqual(a.eta_s, a.distance_m / 10, delta=1)
        self.assertEqual(a.to_dict()["eta_min"], round(a.eta_s / 60))

    def test_offline_and_inactive_buses_skipped(self):
        self.assertEqual(self.arrivals(FixedProvider(MIDDLE, online=False), self.east), [])
        self.bus.is_active = False
        self.bus.save()
        self.assertEqual(self.arrivals(FixedProvider(MIDDLE), self.east), [])

    def test_soonest_first(self):
        Bus.objects.create(route=self.route, plate="ETA2", mock_offset=0.25)
        provider = MockProvider(clock=lambda: 0)
        arrivals = self.arrivals(provider, self.east)
        self.assertEqual(len(arrivals), 2)
        self.assertLessEqual(arrivals[0].eta_s, arrivals[1].eta_s)


class DirectionTests(Base):
    def test_mock_direction_follows_phase(self):
        self.bus.mock_offset = 0.1
        self.assertTrue(MockProvider(clock=lambda: 0).is_moving_forward(self.bus))
        self.bus.mock_offset = 0.7
        self.assertFalse(MockProvider(clock=lambda: 0).is_moving_forward(self.bus))

    def test_gps_direction_from_last_two_points(self):
        older = BusPosition.objects.create(bus=self.bus, lat=41.43, lng=75.975)
        BusPosition.objects.filter(pk=older.pk).update(recorded_at=timezone.now() - timedelta(seconds=10))
        BusPosition.objects.create(bus=self.bus, lat=41.43, lng=75.972)  # moved west
        self.assertFalse(DriverGPSProvider().is_moving_forward(self.bus))

    def test_gps_with_one_point_assumes_forward(self):
        BusPosition.objects.create(bus=self.bus, lat=41.43, lng=75.975)
        self.assertTrue(DriverGPSProvider().is_moving_forward(self.bus))


class StopEtaApiTests(Base):
    def setUp(self):
        super().setUp()
        RouteService.save(self.route, [{"name": "East", "lat": EAST[0], "lng": EAST[1]}])
        self.stop = self.route.ordered_stops()[0]

    def test_returns_arrivals(self):
        data = self.client.get(reverse("api_stop_eta", args=[self.route.pk, self.stop.pk])).json()
        self.assertEqual(data["stop"], {"id": self.stop.pk, "name": "East"})
        self.assertEqual(data["arrivals"][0]["plate"], "TEST1")
        self.assertEqual(set(data["arrivals"][0]), {"bus_id", "plate", "distance_m", "eta_s", "eta_min"})

    def test_stop_of_other_route_is_404(self):
        other = Route.objects.create(number="8", name="Other", path=LINE)
        url = reverse("api_stop_eta", args=[other.pk, self.stop.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_route_detail_includes_stop_ids(self):
        data = self.client.get(reverse("api_route_detail", args=[self.route.pk])).json()
        self.assertEqual(data["stops"][0]["id"], self.stop.pk)
