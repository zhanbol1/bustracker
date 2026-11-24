"""Fills the database with demo data: python manage.py load_demo

Route coordinates are approximate, for demonstration only.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from transit.models import Bus, Mark, MarkCategory, Route
from transit.services.routes import RouteService

ROUTES = [
    {
        "number": "1", "name": "West — Center — East", "color": "#2563eb",
        "path": [[41.4335, 75.9400], [41.4330, 75.9550], [41.4322, 75.9700], [41.4310, 75.9850],
                 [41.4300, 75.9950], [41.4290, 76.0100], [41.4275, 76.0250], [41.4260, 76.0400]],
        "stops": [("West District", 41.4335, 75.9400), ("West Street 2", 41.4322, 75.9700),
                  ("Center", 41.4300, 75.9950), ("East Street 1", 41.4290, 76.0100),
                  ("East District", 41.4260, 76.0400)],
        "buses": ["06 KG 101 ABC", "06 KG 102 ABC", "06 KG 103 ABC"],
    },
    {
        "number": "2", "name": "Center — North District", "color": "#db2777",
        "path": [[41.4300, 75.9950], [41.4330, 75.9960], [41.4360, 75.9980], [41.4395, 76.0000],
                 [41.4420, 76.0040]],
        "stops": [("Center", 41.4300, 75.9950), ("North Street", 41.4360, 75.9980),
                  ("North District", 41.4420, 76.0040)],
        "buses": ["06 KG 201 ABC", "06 KG 202 ABC"],
    },
    {
        "number": "3", "name": "Center — South Bank", "color": "#16a34a",
        "path": [[41.4300, 75.9950], [41.4270, 75.9930], [41.4240, 75.9900], [41.4210, 75.9850]],
        "stops": [("Center", 41.4300, 75.9950), ("Bridge area", 41.4255, 75.9915),
                  ("South Bank", 41.4210, 75.9850)],
        "buses": ["06 KG 301 ABC"],
    },
]

CATEGORIES = [("Cafe", "☕"), ("Pharmacy", "💊"), ("ATM", "🏧"), ("Shop", "🛒"), ("Park", "🌳")]

MARKS = [
    ("Cafe", "Cozy coffee shop", "Good coffee and power outlets by the window.", 41.4308, 75.9930),
    ("Park", "City park", "Shady in summer, a nice place to wait for the bus.", 41.4315, 75.9975),
    ("Pharmacy", "Pharmacy by the stop", "", 41.4292, 76.0105),
    ("ATM", "ATM in the center", "", 41.4298, 75.9960),
]


class Command(BaseCommand):
    help = "Load demo data (routes, buses, users, marks)"

    @transaction.atomic
    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
        if created:
            admin.set_password("admin12345"); admin.save()
        user, created = User.objects.get_or_create(username="aibek")
        if created:
            user.set_password("demo12345"); user.save()

        for data in ROUTES:
            route, _ = Route.objects.update_or_create(
                number=data["number"], defaults={"name": data["name"], "color": data["color"], "path": data["path"]})
            RouteService.save(route, [{"name": n, "lat": la, "lng": ln} for n, la, ln in data["stops"]])
            for i, plate in enumerate(data["buses"]):
                Bus.objects.update_or_create(
                    plate=plate, defaults={"route": route, "mock_offset": i / len(data["buses"])})

        cats = {name: MarkCategory.objects.get_or_create(name=name, defaults={"icon": icon})[0]
                for name, icon in CATEGORIES}
        for cat, title, desc, lat, lng in MARKS:
            Mark.objects.get_or_create(owner=user, title=title,
                                       defaults={"category": cats[cat], "description": desc, "lat": lat, "lng": lng})

        self.stdout.write(self.style.SUCCESS(
            "Done. Admin: admin / admin12345 · User: aibek / demo12345"))
