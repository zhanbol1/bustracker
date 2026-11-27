from django.test import TestCase
from django.urls import reverse


class MapTilesTests(TestCase):
    """OSM blocks tiles without a Referer (issue #5)."""

    def test_pages_send_origin_as_referrer(self):
        r = self.client.get(reverse("map"))
        self.assertEqual(r["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_tiles_use_single_osm_host(self):
        r = self.client.get(reverse("map"))
        self.assertContains(r, "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
        self.assertNotContains(r, "{s}.tile.openstreetmap.org")
