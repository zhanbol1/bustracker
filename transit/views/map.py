from django.shortcuts import render

from ..models import MarkCategory


def map_view(request):
    return render(request, "transit/map.html", {"categories": MarkCategory.objects.all()})
