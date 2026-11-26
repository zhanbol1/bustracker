from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Approximate bounds of Naryn. Marks and stops outside this area are rejected.
CITY_BOUNDS = {"lat_min": 41.38, "lat_max": 41.48, "lng_min": 75.88, "lng_max": 76.10}


def validate_in_city(lat, lng):
    b = CITY_BOUNDS
    if not (b["lat_min"] <= lat <= b["lat_max"] and b["lng_min"] <= lng <= b["lng_max"]):
        raise ValidationError("This point is outside the city.")


class TimeStampedModel(models.Model):
    """Abstract base model (inheritance): shared timestamp fields for all models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Route(TimeStampedModel):
    number = models.CharField("Number", max_length=10, unique=True)
    name = models.CharField("Name", max_length=120)
    color = models.CharField("Line color", max_length=7, default="#2563eb")
    # Route line: list of points [[lat, lng], ...], drawn by an admin on the map
    path = models.JSONField("Route line", default=list)
    is_active = models.BooleanField("Active", default=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"#{self.number} — {self.name}"

    def clean(self):
        if not isinstance(self.path, list) or len(self.path) < 2:
            raise ValidationError("A route line needs at least 2 points.")
        for point in self.path:
            if not (isinstance(point, (list, tuple)) and len(point) == 2):
                raise ValidationError("Invalid route point format.")
            validate_in_city(float(point[0]), float(point[1]))

    def ordered_stops(self):
        return [rs.stop for rs in self.route_stops.select_related("stop").order_by("order")]


class Stop(TimeStampedModel):
    name = models.CharField("Name", max_length=120)
    lat = models.FloatField()
    lng = models.FloatField()

    def __str__(self):
        return self.name

    def clean(self):
        validate_in_city(self.lat, self.lng)


class RouteStop(models.Model):
    """Many-to-many link Route <-> Stop with stop order."""

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="route_stops")
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name="route_stops")
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["route", "order"], name="unique_stop_order_per_route"),
        ]


class Bus(TimeStampedModel):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="buses")
    plate = models.CharField("Plate number", max_length=15, unique=True)
    is_active = models.BooleanField("In service", default=True)
    # One driver drives one bus; the database enforces it with a unique column
    driver = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bus", verbose_name="Driver",
    )
    # Mock bus offset along the route (0..1) so buses do not overlap
    mock_offset = models.FloatField(
        default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

    def __str__(self):
        return f"{self.plate} (route {self.route.number})"


class MarkCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=4, default="📍")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Mark categories"

    def __str__(self):
        return f"{self.icon} {self.name}"


class Mark(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marks")
    category = models.ForeignKey(MarkCategory, on_delete=models.PROTECT, related_name="marks")
    title = models.CharField("Name", max_length=100)
    description = models.TextField("Description", blank=True, max_length=500)
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.lat is not None and self.lng is not None:
            validate_in_city(self.lat, self.lng)

    # Encapsulation: the "who may edit this mark" rule lives in the model, not in the view
    def can_edit(self, user):
        return user.is_authenticated and (user == self.owner or user.is_staff)


class BusPosition(models.Model):
    """Position sent by a driver's phone (for the future DriverGPSProvider)."""

    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="positions")
    lat = models.FloatField()
    lng = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
