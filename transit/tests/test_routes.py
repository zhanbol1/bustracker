from django.urls import reverse

from transit.models import Route

from .base import PATH, Base


class RouteViewTests(Base):
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

    def test_bus_api_returns_positions(self):
        data = self.client.get(reverse("api_route_buses", args=[self.route.pk])).json()
        self.assertEqual(data["buses"][0]["plate"], "TEST1")
