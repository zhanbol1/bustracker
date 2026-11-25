from django.contrib.auth.models import User
from django.test import TestCase

from transit.models import Bus, Mark, MarkCategory, Route

PATH = [[41.4300, 75.9700], [41.4300, 75.9900]]


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pass12345")
        self.other = User.objects.create_user("u2", password="pass12345")
        self.admin = User.objects.create_user("adm", password="pass12345", is_staff=True)
        self.cat = MarkCategory.objects.create(name="Cafe", icon="☕")
        self.route = Route.objects.create(number="1", name="Test", path=PATH)
        self.bus = Bus.objects.create(route=self.route, plate="TEST1")

    def new_mark(self, lat=41.430, lng=75.990, **kw):
        return Mark(category=self.cat, title=kw.get("title", "Coffee"), lat=lat, lng=lng)
