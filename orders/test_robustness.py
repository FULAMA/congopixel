from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Category, Product, ProductVariant
from core.models import SiteSettings

from .models import DeliveryZone, Order
from .services import expire_stale_orders


class RobustnessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        category = Category.objects.create(name="Coques", slug="coques")
        product = Product.objects.create(
            category=category, name="Coque", slug="coque", price_usd=Decimal("10.00")
        )
        cls.variant = ProductVariant.objects.create(product=product, name="Noir", stock=20)
        cls.zone = DeliveryZone.objects.create(name="Kinshasa", fee_usd=Decimal("2.00"))

    def setUp(self):
        cache.clear()

    def place_order(self, client, method="orange_money"):
        client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": 1})
        return client.post(reverse("orders:checkout"), {
            "full_name": "Client Test", "phone": "0812345678", "email": "",
            "city": "Kinshasa", "address": "Avenue Test 1",
            "delivery_zone": self.zone.pk, "notes": "", "payment_method": method,
        })

    def age(self, order, hours=30):
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=hours))

    def test_unpaid_mobile_money_order_expires_and_restocks(self):
        self.place_order(Client())
        order = Order.objects.get()
        self.age(order)
        self.assertEqual(expire_stale_orders(), 1)
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.variant.stock, 20)

    def test_orders_that_must_stay_are_not_expired(self):
        self.place_order(Client(), "cash_on_delivery")
        paying = Client()
        self.place_order(paying)
        cod = Order.objects.filter(payments__method="cash_on_delivery").get()
        mobile = Order.objects.exclude(pk=cod.pk).get()
        paying.post(
            reverse("orders:payment", args=[mobile.reference]),
            {"transaction_id": "ABC123456", "payer_phone": "0812345678"},
        )
        self.age(cod)
        self.age(mobile)
        self.assertEqual(expire_stale_orders(), 0)

    def test_checkout_is_rate_limited_per_session(self):
        client = Client()
        for _ in range(5):
            self.place_order(client)
        self.assertEqual(Order.objects.count(), 5)
        response = self.place_order(client)
        self.assertEqual(Order.objects.count(), 5)
        self.assertRedirects(response, reverse("cart:detail"))

    def test_custom_404_page(self):
        response = self.client.get("/cette-page-nexiste-pas/")
        self.assertContains(response, "cette page n'existe pas", status_code=404)