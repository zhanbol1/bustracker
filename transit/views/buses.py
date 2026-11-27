"""Bus admin pages: list, create, edit, delete. Staff only."""
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.shortcuts import render

from ..models import Bus, Route

staff_required = user_passes_test(lambda u: u.is_staff)


@staff_required
def bus_list(request):
    buses = Bus.objects.select_related("route", "driver").order_by("route__number", "plate")
    q = request.GET.get("q", "").strip()
    if q:
        buses = buses.filter(Q(plate__icontains=q) | Q(driver__username__icontains=q))
    route_id = request.GET.get("route", "")
    if route_id.isdigit():
        buses = buses.filter(route_id=route_id)
    return render(request, "transit/bus_list.html", {
        "buses": buses, "routes": Route.objects.all(), "q": q, "route_id": route_id,
    })
