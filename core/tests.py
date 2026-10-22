import io
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from catalog.models import Category, Product, ProductVariant
from orders.models import DeliveryZone, Order


class PublicPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Coques", slug="coques")
        cls.product = Product.objects.create(
            category=category, name="Coque <b>Pixel</b>", slug="coque-pixel", price_usd=Decimal("10.00")
        )
        ProductVariant.objects.create(product=cls.product, name="Noir", stock=5)

    def test_trust_pages_load(self):
        for name in ("core:shipping_returns", "core:terms", "core:about"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertContains(response, "Sitemap:")
        self.assertContains(response, "Disallow: /panier/")

    def test_sitemap_lists_product(self):
        response = self.client.get("/sitemap.xml")
        self.assertContains(response, "/produit/coque-pixel/")

    def test_product_page_has_safe_jsonld(self):
        response = self.client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertContains(response, "application/ld+json")
        self.assertNotContains(response, "<b>Pixel</b>")


class AdminToolsTests(TestCase):
    def test_setup_groups_is_idempotent(self):
        call_command("setup_groups", stdout=io.StringIO())
        call_command("setup_groups", stdout=io.StringIO())
        self.assertEqual(Group.objects.count(), 2)
        group = Group.objects.get(name="Gestionnaire de commandes")
        self.assertTrue(group.permissions.filter(codename="change_order").exists())
        self.assertFalse(group.permissions.filter(codename="delete_order").exists())

    def test_csv_export_neutralizes_formulas(self):
        boss = User.objects.create_superuser("boss", password="Un-mot-de-passe-solide-42")
        self.client.force_login(boss)
        zone = DeliveryZone.objects.create(name="Kinshasa")
        order = Order.objects.create(
            full_name='=HYPERLINK("x")', phone="243812345678", city="Kinshasa",
            address="Avenue 1", delivery_zone=zone,
        )
        response = self.client.post(
            reverse("admin:orders_order_changelist"),
            {"action": "export_orders_csv", "_selected_action": [order.pk]},
        )
        content = response.content.decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", content)
        self.assertNotIn('"=HYPERLINK', content)