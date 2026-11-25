"""JSON API used by the map page."""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models import Route
from ..services import location_provider
from .marks import filter_marks
from .routes import search_routes


def api_routes(request):
    q = request.GET.get("q", "").strip()
    data = [{"id": r.id, "number": r.number, "name": r.name, "color": r.color}
            for r in search_routes(q)]
    return JsonResponse({"routes": data})


def api_route_detail(request, pk):
    r = get_object_or_404(Route, pk=pk, is_active=True)
    return JsonResponse({
        "id": r.id, "number": r.number, "name": r.name, "color": r.color, "path": r.path,
        "stops": [{"name": s.name, "lat": s.lat, "lng": s.lng} for s in r.ordered_stops()],
    })


def api_route_buses(request, pk):
    route = get_object_or_404(Route, pk=pk)
    buses = route.buses.filter(is_active=True).select_related("route")
    return JsonResponse({"buses": [loc.to_dict() for loc in location_provider.get_positions(buses)]})


def api_marks(request):
    marks = filter_marks(request.GET).select_related("category", "owner")
    return JsonResponse({"marks": [{
        "id": m.id, "title": m.title, "description": m.description, "lat": m.lat, "lng": m.lng,
        "icon": m.category.icon, "category": m.category.name, "owner": m.owner.username,
        "can_edit": m.can_edit(request.user),
    } for m in marks]})
