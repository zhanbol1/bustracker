from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import MarkForm, RouteForm, SignUpForm
from .models import Mark, MarkCategory, Route
from .services import MarkService, location_provider
from .services.routes import RouteService

staff_required = user_passes_test(lambda u: u.is_staff)


# ---------- Home: map ----------

def map_view(request):
    return render(request, "transit/map.html", {"categories": MarkCategory.objects.all()})


# ---------- JSON API for the map ----------

def search_routes(q, include_inactive=False):
    routes = Route.objects.all() if include_inactive else Route.objects.filter(is_active=True)
    if q:
        routes = routes.filter(Q(number__icontains=q) | Q(name__icontains=q)
                               | Q(route_stops__stop__name__icontains=q)).distinct()
    return routes


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


# ---------- Marks (CRUD) ----------

SORTS = {"new": "-created_at", "old": "created_at", "title": "title"}


def filter_marks(params):
    marks = Mark.objects.all()
    q = params.get("q", "").strip()
    if q:
        marks = marks.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if params.get("category"):
        marks = marks.filter(category_id=params["category"])
    return marks.order_by(SORTS.get(params.get("sort"), "-created_at"))


def mark_list(request):
    marks = filter_marks(request.GET).select_related("category", "owner")
    return render(request, "transit/mark_list.html", {
        "marks": marks, "categories": MarkCategory.objects.all(), "params": request.GET,
    })


@login_required
def my_marks(request):
    marks = Mark.objects.filter(owner=request.user).select_related("category")
    return render(request, "transit/mark_list.html", {"marks": marks, "mine": True})


def mark_detail(request, pk):
    mark = get_object_or_404(Mark.objects.select_related("category", "owner"), pk=pk)
    return render(request, "transit/mark_detail.html",
                  {"mark": mark, "can_edit": mark.can_edit(request.user)})


def _save_mark(request, form, action):
    """Shared create/update logic: business rule errors are shown on the form."""
    if form.is_valid():
        try:
            mark = action(form.save(commit=False))
            messages.success(request, "Mark saved.")
            return redirect("mark_detail", pk=mark.pk)
        except ValidationError as e:
            for msg in e.messages:
                form.add_error(None, msg)
    return None


@login_required
def mark_create(request):
    service = MarkService(request.user)
    if request.method == "POST":
        form = MarkForm(request.POST)
        response = _save_mark(request, form, service.create)
        if response:
            return response
    else:
        form = MarkForm(initial={"lat": request.GET.get("lat"), "lng": request.GET.get("lng")})
    return render(request, "transit/mark_form.html", {"form": form, "title": "New mark"})


@login_required
def mark_update(request, pk):
    mark = get_object_or_404(Mark, pk=pk)
    if not mark.can_edit(request.user):
        raise PermissionDenied
    service = MarkService(request.user)
    form = MarkForm(request.POST or None, instance=mark)
    if request.method == "POST":
        response = _save_mark(request, form, service.update)
        if response:
            return response
    return render(request, "transit/mark_form.html", {"form": form, "title": "Edit mark"})


@login_required
def mark_delete(request, pk):
    mark = get_object_or_404(Mark, pk=pk)
    if not mark.can_edit(request.user):
        raise PermissionDenied
    if request.method == "POST":
        MarkService(request.user).delete(mark)
        messages.success(request, "Mark deleted.")
        return redirect("my_marks")
    return render(request, "transit/confirm_delete.html", {"obj": mark, "cancel_url": reverse("mark_detail", args=[pk])})


# ---------- Routes ----------

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


# ---------- Sign-up ----------

def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! You can now add marks.")
        return redirect("map")
    return render(request, "registration/signup.html", {"form": form})
