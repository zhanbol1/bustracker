"""JSON API used by the map page and the driver page."""
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import Bus, Route
from ..services import BusTrackingService, location_provider
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


@require_POST
def api_bus_position(request, pk):
    """A driver's phone sends {"lat": .., "lng": ..}; see BusTrackingService for the rules."""
    bus = get_object_or_404(Bus, pk=pk)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Log in as the driver of this bus."}, status=401)
    try:
        data = json.loads(request.body)
        lat, lng = float(data["lat"]), float(data["lng"])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": 'Send JSON like {"lat": 41.43, "lng": 75.99}.'}, status=400)
    try:
        pos = BusTrackingService(request.user).record(bus, lat, lng)
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    except ValidationError as e:
        return JsonResponse({"error": " ".join(e.messages)}, status=400)
    return JsonResponse({
        "bus": bus.id, "plate": bus.plate, "lat": pos.lat, "lng": pos.lng,
        "recorded_at": pos.recorded_at.isoformat(),
    }, status=201)
