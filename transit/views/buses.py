"""Bus admin pages: list, create, edit, delete. Staff only."""
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import BusForm
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


@staff_required
def bus_edit(request, pk=None):
    bus = get_object_or_404(Bus, pk=pk) if pk else Bus()
    form = BusForm(request.POST or None, instance=bus)
    if request.method == "POST" and form.is_valid():
        bus = form.save()
        messages.success(request, f"Bus {bus.plate} saved.")
        return redirect("bus_list")
    return render(request, "transit/bus_form.html",
                  {"form": form, "bus": bus, "title": f"Edit bus {bus.plate}" if pk else "New bus"})


@staff_required
def bus_delete(request, pk):
    bus = get_object_or_404(Bus, pk=pk)
    if request.method == "POST":
        bus.delete()
        messages.success(request, f"Bus {bus.plate} deleted.")
        return redirect("bus_list")
    return render(request, "transit/confirm_delete.html", {"obj": bus, "cancel_url": reverse("bus_update", args=[pk])})
