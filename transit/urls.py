from django.urls import path

from . import views

urlpatterns = [
    path("", views.map_view, name="map"),
    # JSON API for the map
    path("api/routes/", views.api_routes, name="api_routes"),
    path("api/routes/<int:pk>/", views.api_route_detail, name="api_route_detail"),
    path("api/routes/<int:pk>/buses/", views.api_route_buses, name="api_route_buses"),
    path("api/routes/<int:pk>/stops/<int:stop_id>/eta/", views.api_stop_eta, name="api_stop_eta"),
    path("api/marks/", views.api_marks, name="api_marks"),
    path("api/buses/<int:pk>/position/", views.api_bus_position, name="api_bus_position"),
    # Marks
    path("marks/", views.mark_list, name="mark_list"),
    path("marks/mine/", views.my_marks, name="my_marks"),
    path("marks/new/", views.mark_create, name="mark_create"),
    path("marks/<int:pk>/", views.mark_detail, name="mark_detail"),
    path("marks/<int:pk>/edit/", views.mark_update, name="mark_update"),
    path("marks/<int:pk>/delete/", views.mark_delete, name="mark_delete"),
    # Routes
    path("routes/", views.route_list, name="route_list"),
    path("routes/new/", views.route_edit, name="route_create"),
    path("routes/<int:pk>/", views.route_detail, name="route_detail"),
    path("routes/<int:pk>/edit/", views.route_edit, name="route_update"),
    path("routes/<int:pk>/delete/", views.route_delete, name="route_delete"),
    # Driver page
    path("driver/", views.driver_page, name="driver"),
    # Buses (admin only)
    path("buses/", views.bus_list, name="bus_list"),
    path("buses/new/", views.bus_edit, name="bus_create"),
    path("buses/<int:pk>/edit/", views.bus_edit, name="bus_update"),
    path("buses/<int:pk>/delete/", views.bus_delete, name="bus_delete"),
    # Sign-up
    path("signup/", views.signup, name="signup"),
]
