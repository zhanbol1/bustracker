from django.contrib.auth.models import User
from django.urls import reverse

from transit.forms import BusForm
from transit.models import Bus, Route

from .base import PATH, Base


class BusAdminBase(Base):
    def setUp(self):
        super().setUp()
        self.client.login(username="adm", password="pass12345")

    def form_data(self, **kw):
        data = {"plate": "NEW1", "route": self.route.pk, "driver": "", "is_active": "on"}
        data.update(kw)
        return data


class BusAccessTests(Base):
    def test_guest_is_sent_to_login(self):
        r = self.client.get(reverse("bus_list"))
        self.assertRedirects(r, reverse("login") + "?next=" + reverse("bus_list"))

    def test_regular_user_cannot_open_any_bus_page(self):
        self.client.login(username="u1", password="pass12345")
        for url in [reverse("bus_list"), reverse("bus_create"),
                    reverse("bus_update", args=[self.bus.pk]), reverse("bus_delete", args=[self.bus.pk])]:
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_regular_user_cannot_delete_by_post(self):
        self.client.login(username="u1", password="pass12345")
        self.client.post(reverse("bus_delete", args=[self.bus.pk]))
        self.assertTrue(Bus.objects.filter(pk=self.bus.pk).exists())


class BusListTests(BusAdminBase):
    def setUp(self):
        super().setUp()
        self.other_route = Route.objects.create(number="7", name="Other", path=PATH)
        Bus.objects.create(route=self.other_route, plate="ABC777", driver=self.other)

    def plates(self, **params):
        return [b.plate for b in self.client.get(reverse("bus_list"), params).context["buses"]]

    def test_lists_all_buses(self):
        self.assertEqual(sorted(self.plates()), ["ABC777", "TEST1"])

    def test_search_by_plate(self):
        self.assertEqual(self.plates(q="777"), ["ABC777"])

    def test_search_by_driver(self):
        self.assertEqual(self.plates(q="u2"), ["ABC777"])

    def test_filter_by_route(self):
        self.assertEqual(self.plates(route=self.route.pk), ["TEST1"])

    def test_empty_search_message(self):
        self.assertContains(self.client.get(reverse("bus_list"), {"q": "zzz"}), "No buses match your search")


class BusFormTests(BusAdminBase):
    def test_create_bus_with_driver(self):
        r = self.client.post(reverse("bus_create"), self.form_data(driver=self.user.pk))
        self.assertRedirects(r, reverse("bus_list"))
        self.assertEqual(Bus.objects.get(plate="NEW1").driver, self.user)

    def test_edit_bus(self):
        self.client.post(reverse("bus_update", args=[self.bus.pk]), self.form_data(plate="TEST1-B"))
        self.bus.refresh_from_db()
        self.assertEqual(self.bus.plate, "TEST1-B")

    def test_duplicate_plate_shows_error(self):
        r = self.client.post(reverse("bus_create"), self.form_data(plate="TEST1"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("plate", r.context["form"].errors)

    def test_dropdown_hides_users_who_drive_another_bus(self):
        self.bus.driver = self.user
        self.bus.save()
        choices = list(BusForm().fields["driver"].queryset)
        self.assertNotIn(self.user, choices)
        self.assertIn(self.other, choices)

    def test_dropdown_keeps_current_driver_when_editing(self):
        self.bus.driver = self.user
        self.bus.save()
        self.assertIn(self.user, BusForm(instance=self.bus).fields["driver"].queryset)

    def test_driver_of_another_bus_cannot_be_posted(self):
        self.bus.driver = self.user
        self.bus.save()
        r = self.client.post(reverse("bus_create"), self.form_data(driver=self.user.pk))
        self.assertIn("driver", r.context["form"].errors)
        self.assertFalse(Bus.objects.filter(plate="NEW1").exists())

    def test_inactive_user_not_offered(self):
        User.objects.create_user("gone", password="x", is_active=False)
        names = [u.username for u in BusForm().fields["driver"].queryset]
        self.assertNotIn("gone", names)


class BusDeleteTests(BusAdminBase):
    def test_get_shows_confirmation(self):
        r = self.client.get(reverse("bus_delete", args=[self.bus.pk]))
        self.assertContains(r, "Yes, delete")
        self.assertTrue(Bus.objects.filter(pk=self.bus.pk).exists())

    def test_post_deletes(self):
        r = self.client.post(reverse("bus_delete", args=[self.bus.pk]))
        self.assertRedirects(r, reverse("bus_list"))
        self.assertFalse(Bus.objects.filter(pk=self.bus.pk).exists())
