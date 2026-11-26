from django.contrib import admin

from .models import Bus, BusPosition, Mark, MarkCategory, Route, RouteStop, Stop


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 1


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "is_active"]
    inlines = [RouteStopInline]


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ["plate", "route", "driver", "is_active"]
    list_filter = ["route", "is_active"]
    search_fields = ["plate", "driver__username"]


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "owner", "created_at"]
    list_filter = ["category"]
    search_fields = ["title"]


admin.site.register([Stop, MarkCategory, BusPosition])
