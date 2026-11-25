from django.test import TestCase

from transit.services.geo import Polyline, distance_m

from .base import PATH


class GeoTests(TestCase):
    def test_distance(self):
        # ~1 degree of longitude at latitude 42.87 is about 81.6 km
        self.assertAlmostEqual(distance_m(42.87, 74.0, 42.87, 75.0) / 1000, 81.6, delta=0.5)

    def test_polyline_endpoints(self):
        line = Polyline(PATH)
        self.assertEqual(line.point_at(0), tuple(PATH[0]))
        self.assertAlmostEqual(line.point_at(1)[1], PATH[1][1])
