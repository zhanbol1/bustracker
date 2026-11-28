from django.urls import reverse

from .base import Base


class DriverPageTests(Base):
    def test_guest_is_sent_to_login(self):
        r = self.client.get(reverse("driver"))
        self.assertRedirects(r, reverse("login") + "?next=" + reverse("driver"))

    def test_user_without_bus_gets_403(self):
        self.client.login(username="u2", password="pass12345")
        self.assertEqual(self.client.get(reverse("driver")).status_code, 403)

    def test_admin_without_bus_gets_403(self):
        self.client.login(username="adm", password="pass12345")
        self.assertEqual(self.client.get(reverse("driver")).status_code, 403)

    def test_driver_sees_own_bus_and_api_url(self):
        self.bus.driver = self.user
        self.bus.save()
        self.client.login(username="u1", password="pass12345")
        r = self.client.get(reverse("driver"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "TEST1")
        self.assertContains(r, f'data-url="{reverse("api_bus_position", args=[self.bus.pk])}"')
        self.assertContains(r, "transit/driver.js")

    def test_bus_not_in_service_shows_warning(self):
        self.bus.driver = self.user
        self.bus.is_active = False
        self.bus.save()
        self.client.login(username="u1", password="pass12345")
        self.assertContains(self.client.get(reverse("driver")), "not in service")


class DriverLinkTests(Base):
    def test_driver_sees_link(self):
        self.bus.driver = self.user
        self.bus.save()
        self.client.login(username="u1", password="pass12345")
        self.assertContains(self.client.get(reverse("map")), f'href="{reverse("driver")}"')

    def test_other_user_does_not(self):
        self.client.login(username="u2", password="pass12345")
        self.assertNotContains(self.client.get(reverse("map")), f'href="{reverse("driver")}"')
