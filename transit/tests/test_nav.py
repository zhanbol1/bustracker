from django.urls import reverse

from .base import Base


class NavigationTests(Base):
    def test_menu_button_is_rendered(self):
        r = self.client.get(reverse("route_list"))
        self.assertContains(r, 'class="nav-toggle"')
        self.assertContains(r, 'aria-controls="site-nav"')

    def test_current_page_is_highlighted(self):
        r = self.client.get(reverse("route_list"))
        self.assertContains(r, f'<a href="{reverse("route_list")}" class="active" aria-current="page">Routes</a>', html=True)
        self.assertContains(r, 'aria-current="page"', count=1)

    def test_detail_page_highlights_its_section(self):
        r = self.client.get(reverse("route_detail", args=[self.route.pk]))
        self.assertContains(r, f'<a href="{reverse("route_list")}" class="active" aria-current="page">Routes</a>', html=True)

    def test_staff_link_highlighted_for_admin(self):
        self.client.login(username="adm", password="pass12345")
        r = self.client.get(reverse("route_create"))
        self.assertContains(r, f'<a href="{reverse("route_create")}" class="active" aria-current="page">+ Route</a>', html=True)
