from django.db import transaction

from ..models import RouteStop, Stop


class RouteService:
    """Saves a route together with its ordered list of stops."""

    @staticmethod
    @transaction.atomic
    def save(route, stops):
        route.full_clean()  # validates the line: >= 2 points, all inside the city
        route.save()
        route.route_stops.all().delete()
        for order, s in enumerate(stops, start=1):
            stop, _ = Stop.objects.get_or_create(name=s["name"], lat=s["lat"], lng=s["lng"])
            RouteStop.objects.create(route=route, stop=stop, order=order)
        return route
