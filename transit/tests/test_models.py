from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from transit.models import Bus, BusPosition, Stop
from transit.services.routes import RouteService

from .base import Base


class BusDriverTests(Base):
    def test_driver_reaches_bus_through_user(self):
        self.bus.driver = self.user
        self.bus.save()
        self.assertEqual(User.objects.get(pk=self.user.pk).bus, self.bus)

    def test_bus_without_driver_is_allowed(self):
        self.assertIsNone(Bus.objects.get(pk=self.bus.pk).driver)

    def test_one_driver_cannot_drive_two_buses(self):
        self.bus.driver = self.user
        self.bus.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Bus.objects.create(route=self.route, plate="TEST2", driver=self.user)

    def test_deleting_driver_keeps_bus(self):
        self.bus.driver = self.user
        self.bus.save()
        self.user.delete()
        self.assertIsNone(Bus.objects.get(pk=self.bus.pk).driver)


class StopConstraintTests(Base):
    def test_same_stop_twice_is_rejected(self):
        Stop.objects.create(name="Center", lat=41.43, lng=75.995)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Stop.objects.create(name="Center", lat=41.43, lng=75.995)

    def test_same_name_at_other_place_is_allowed(self):
        Stop.objects.create(name="Center", lat=41.43, lng=75.995)
        Stop.objects.create(name="Center", lat=41.44, lng=75.995)
        self.assertEqual(Stop.objects.filter(name="Center").count(), 2)

    def test_routes_share_one_stop(self):
        stop = {"name": "Center", "lat": 41.43, "lng": 75.98}
        RouteService.save(self.route, [stop])
        other = type(self.route)(number="2", name="Other", path=self.route.path)
        RouteService.save(other, [stop])
        self.assertEqual(Stop.objects.count(), 1)


class BusPositionIndexTests(Base):
    def test_latest_position_index_exists(self):
        indexes = {i.name: i.fields for i in BusPosition._meta.indexes}
        self.assertEqual(indexes["busposition_bus_time_idx"], ["bus", "recorded_at"])
