from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import RouteForm
from ..models import Route
from ..services.routes import RouteService

staff_required = user_passes_test(lambda u: u.is_staff)


def search_routes(q, include_inactive=False):
    routes = Route.objects.all() if include_inactive else Route.objects.filter(is_active=True)
    if q:
        routes = routes.filter(Q(number__icontains=q) | Q(name__icontains=q)
                               | Q(route_stops__stop__name__icontains=q)).distinct()
    return routes


def route_list(request):
    q = request.GET.get("q", "").strip()
    routes = search_routes(q, include_inactive=request.user.is_staff)
    return render(request, "transit/route_list.html", {"routes": routes, "q": q})


def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    return render(request, "transit/route_detail.html", {"route": route, "stops": route.ordered_stops()})


@staff_required
def route_edit(request, pk=None):
    route = get_object_or_404(Route, pk=pk) if pk else Route()
    form = RouteForm(request.POST or None, instance=route)
    if request.method == "POST" and form.is_valid():
        try:
            route = form.save(commit=False)
            RouteService.save(route, form.cleaned_data["stops"])
            messages.success(request, "Route saved.")
            return redirect("route_detail", pk=route.pk)
        except ValidationError as e:
            for msg in e.messages:
                form.add_error(None, msg)
    return render(request, "transit/route_form.html",
                  {"form": form, "title": "Edit route" if pk else "New route"})


@staff_required
def route_delete(request, pk):
    route = get_object_or_404(Route, pk=pk)
    if request.method == "POST":
        route.delete()
        messages.success(request, "Route deleted.")
        return redirect("route_list")
    return render(request, "transit/confirm_delete.html", {"obj": route, "cancel_url": reverse("route_detail", args=[pk])})
