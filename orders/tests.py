from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Category, Product, ProductVariant
from core.models import SiteSettings
from core.validators import normalize_phone
from payments.models import Payment

from .models import DeliveryZone, Order
from .services import restock_order


class ShopFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        site_settings = SiteSettings.load()
        site_settings.usd_to_cdf_rate = Decimal("2800.00")
        site_settings.orange_money_number = "243810000000"
        site_settings.save()
        category = Category.objects.create(name="Coques", slug="coques")
        product = Product.objects.create(
            category=category, name="Coque Pixel 8", slug="coque-pixel-8", price_usd=Decimal("10.00")
        )
        cls.variant = ProductVariant.objects.create(product=product, name="Noir", stock=5)
        cls.zone = DeliveryZone.objects.create(name="Kinshasa", fee_usd=Decimal("2.00"))

    def setUp(self):
        cache.clear()
        self.client = Client()

    def place_order(self, client, quantity=1, method="orange_money"):
        client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": quantity})
        return client.post(reverse("orders:checkout"), {
            "full_name": "Client Test", "phone": "0812345678", "email": "",
            "city": "Kinshasa", "address": "Avenue Test 1",
            "delivery_zone": self.zone.pk, "notes": "", "payment_method": method,
        })

    def test_checkout_creates_order_and_decrements_stock(self):
        response = self.place_order(self.client, quantity=2)
        order = Order.objects.get()
        self.assertRedirects(response, reverse("orders:payment", args=[order.reference]))
        self.assertEqual(order.total_usd, Decimal("22.00"))
        self.assertEqual(order.phone, "243812345678")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)
        payment = order.payments.get()
        self.assertEqual(payment.method, Payment.Method.ORANGE_MONEY)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.amount_usd, Decimal("22.00"))

    def test_cart_quantity_is_capped_by_stock(self):
        self.client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": 99})
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.context["lines"][0].quantity, 5)

    def test_transaction_id_cannot_be_reused(self):
        self.place_order(self.client)
        first = Order.objects.get()
        self.client.post(
            reverse("orders:payment", args=[first.reference]),
            {"transaction_id": "ABC123456", "payer_phone": "0812345678"},
        )
        other = Client()
        self.place_order(other)
        second = Order.objects.exclude(pk=first.pk).get()
        response = other.post(
            reverse("orders:payment", args=[second.reference]),
            {"transaction_id": "abc 123456", "payer_phone": "0899999999"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("transaction_id", response.context["form"].errors)
        self.assertEqual(second.payments.get().transaction_id, "")

    def test_order_page_is_private(self):
        self.place_order(self.client)
        order = Order.objects.get()
        self.assertEqual(self.client.get(reverse("orders:detail", args=[order.reference])).status_code, 200)
        self.assertEqual(Client().get(reverse("orders:detail", args=[order.reference])).status_code, 404)

    def test_restock_happens_only_once(self):
        self.place_order(self.client, quantity=2)
        order = Order.objects.get()
        self.assertTrue(restock_order(order))
        self.assertFalse(restock_order(order))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5)


class PhoneTests(TestCase):
    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+243 81 234 5678"), "243812345678")
        self.assertEqual(normalize_phone("0812345678"), "243812345678")
        self.assertEqual(normalize_phone("812345678"), "243812345678")
        with self.assertRaises(ValidationError):
            normalize_phone("123")