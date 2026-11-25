from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import MarkForm
from ..models import Mark, MarkCategory
from ..services import MarkService


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
