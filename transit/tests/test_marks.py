from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from transit.models import Mark, Route
from transit.services.marks import MarkService

from .base import Base


class MarkRuleTests(Base):
    def test_create_valid_mark(self):
        mark = MarkService(self.user).create(self.new_mark())
        self.assertEqual(Mark.objects.get(pk=mark.pk).owner, self.user)

    def test_mark_outside_city_rejected(self):
        with self.assertRaises(ValidationError):
            MarkService(self.user).create(self.new_mark(lat=40.0, lng=70.0))

    def test_duplicate_nearby_rejected(self):
        MarkService(self.user).create(self.new_mark())
        with self.assertRaises(ValidationError):
            MarkService(self.user).create(self.new_mark(lat=41.43001, title="More coffee"))

    def test_daily_limit(self):
        for i in range(MarkService.DAILY_LIMIT):
            MarkService(self.user).create(self.new_mark(lat=41.40 + i * 0.002))
        with self.assertRaises(ValidationError):
            MarkService(self.user).create(self.new_mark(lat=41.45))

    def test_other_user_cannot_edit(self):
        mark = MarkService(self.user).create(self.new_mark())
        with self.assertRaises(PermissionDenied):
            MarkService(self.other).delete(mark)

    def test_admin_can_delete_any(self):
        mark = MarkService(self.user).create(self.new_mark())
        MarkService(self.admin).delete(mark)
        self.assertFalse(Mark.objects.exists())

    def test_route_needs_two_points(self):
        with self.assertRaises(ValidationError):
            Route(number="9", name="x", path=[[41.43, 75.99]]).full_clean()


class MarkViewTests(Base):
    def test_guest_sees_map_and_marks(self):
        self.assertEqual(self.client.get(reverse("map")).status_code, 200)
        self.assertEqual(self.client.get(reverse("api_marks")).status_code, 200)

    def test_guest_cannot_create_mark(self):
        r = self.client.get(reverse("mark_create"))
        self.assertRedirects(r, reverse("login") + "?next=" + reverse("mark_create"))

    def test_user_creates_mark_via_form(self):
        self.client.login(username="u1", password="pass12345")
        r = self.client.post(reverse("mark_create"),
                             {"title": "Coffee", "category": self.cat.id, "lat": 41.43, "lng": 75.99})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Mark.objects.count(), 1)

    def test_invalid_form_shows_errors(self):
        self.client.login(username="u1", password="pass12345")
        r = self.client.post(reverse("mark_create"), {"title": "", "category": self.cat.id})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)

    def test_mark_search_empty_message(self):
        r = self.client.get(reverse("mark_list"), {"q": "nonexistent"})
        self.assertContains(r, "Nothing matches your search")
