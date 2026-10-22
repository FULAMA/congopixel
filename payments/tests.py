import uuid
from decimal import Decimal

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from cart.cart import CartLine
from catalog.models import Category, Product, ProductVariant
from core.models import SiteSettings
from orders.models import DeliveryZone, Order
from orders.services import place_order, restock_order

from .models import Payment, PaymentEvent
from .services import (
    ALREADY_CONFIRMED, CONFIRMED, DUPLICATE, ORDER_CANCELLED,
    confirm_payment, record_provider_event,
)


class FakeCart:
    def __init__(self, variant, quantity=1):
        price = variant.unit_price_usd
        self._lines = [CartLine(variant, quantity, price, price * quantity)]

    def lines(self):
        return self._lines


class PaymentIdempotencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        category = Category.objects.create(name="Coques", slug="coques")
        product = Product.objects.create(
            category=category, name="Coque", slug="coque", price_usd=Decimal("10.00")
        )
        cls.variant = ProductVariant.objects.create(product=product, name="Noir", stock=5)
        cls.zone = DeliveryZone.objects.create(name="Kinshasa", fee_usd=Decimal("2.00"))

    def setUp(self):
        cache.clear()

    def data(self):
        return {
            "full_name": "Client Test", "phone": "243812345678", "email": "",
            "city": "Kinshasa", "address": "Avenue Test 1",
            "delivery_zone": self.zone, "notes": "",
        }

    def payload(self, key=None):
        return {
            "full_name": "Client Test", "phone": "0812345678", "email": "",
            "city": "Kinshasa", "address": "Avenue Test 1",
            "delivery_zone": self.zone.pk, "notes": "", "payment_method": "orange_money",
            "idempotency_key": key or str(uuid.uuid4()),
        }

    def make_order(self):
        order, _ = place_order(FakeCart(self.variant), self.data(), "orange_money", idempotency_key=uuid.uuid4())
        return order

    def test_place_order_is_idempotent_for_same_key(self):
        key = uuid.uuid4()
        first, created_first = place_order(FakeCart(self.variant), self.data(), "orange_money", idempotency_key=key)
        second, created_second = place_order(FakeCart(self.variant), self.data(), "orange_money", idempotency_key=key)
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Order.objects.count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 4)

    def test_replayed_checkout_post_returns_same_order(self):
        client = Client()
        client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": 1})
        payload = self.payload()
        first = client.post(reverse("orders:checkout"), payload)
        second = client.post(reverse("orders:checkout"), payload)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(first["Location"], second["Location"])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 4)

    def test_confirm_payment_is_idempotent(self):
        order = self.make_order()
        payment = order.payments.get()
        self.assertEqual(confirm_payment(payment.pk), CONFIRMED)
        self.assertEqual(confirm_payment(payment.pk), ALREADY_CONFIRMED)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)

    def test_cannot_confirm_payment_of_cancelled_order(self):
        order = self.make_order()
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        restock_order(order)
        payment = order.payments.get()
        self.assertEqual(confirm_payment(payment.pk), ORDER_CANCELLED)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_provider_event_is_processed_once(self):
        order = self.make_order()
        first = record_provider_event("orange", "evt-1", order.reference, order.total_usd, "USD", True)
        second = record_provider_event("orange", "evt-1", order.reference, order.total_usd, "USD", True)
        self.assertEqual(first, CONFIRMED)
        self.assertEqual(second, DUPLICATE)
        self.assertEqual(PaymentEvent.objects.count(), 1)

    def test_provider_event_with_wrong_amount_is_not_confirmed(self):
        order = self.make_order()
        outcome = record_provider_event("orange", "evt-2", order.reference, Decimal("1.00"), "USD", True)
        self.assertEqual(outcome, "amount_mismatch")
        self.assertEqual(order.payments.get().status, Payment.Status.PENDING)

    def test_provider_event_in_cdf_matches_locked_rate(self):
        order = self.make_order()
        outcome = record_provider_event("orange", "evt-3", order.reference, order.total_cdf, "CDF", True)
        self.assertEqual(outcome, CONFIRMED)

    def test_proof_submitted_twice_keeps_first_id(self):
        client = Client()
        client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": 1})
        client.post(reverse("orders:checkout"), self.payload())
        order = Order.objects.get()
        url = reverse("orders:payment", args=[order.reference])
        client.post(url, {"transaction_id": "ABC123456", "payer_phone": "0812345678"})
        response = client.post(url, {"transaction_id": "ZZZ999999", "payer_phone": "0812345678"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.payments.get().transaction_id, "ABC123456")