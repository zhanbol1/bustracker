"""Driver page: the phone of a bus's driver shares its location with the server."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render


@login_required
def driver_page(request):
    bus = getattr(request.user, "bus", None)  # set by Bus.driver; missing for non-drivers
    if bus is None:
        raise PermissionDenied("Only users assigned to a bus can open the driver page.")
    return render(request, "transit/driver.html", {"bus": bus})
