import io
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from catalog.models import Category, PixelModel, ProductVariant
from core.testing import PASSWORD, ShopTestCase
from orders.models import DeliveryZone, Order
from payments.models import Payment


class IntegrationTests(ShopTestCase):
    def stock(self):
        return ProductVariant.objects.get(pk=self.variant.pk).stock

    def test_admin_confirmation_marks_order_paid_once(self):
        order = self.order_via_client()
        payment = order.payments.get()
        admin = self.admin_client()
        url = reverse("admin:payments_payment_changelist")
        data = {"action": "confirm_payments", "_selected_action": [payment.pk]}
        admin.post(url, data)
        first_confirmer = Payment.objects.get(pk=payment.pk).confirmed_by_id
        admin.post(url, data)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CONFIRMED)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertIsNotNone(first_confirmer)
        self.assertEqual(payment.confirmed_by_id, first_confirmer)

    def test_admin_cancellation_restocks_exactly_once(self):
        order = self.order_via_client()
        self.assertEqual(self.stock(), 9)
        admin = self.admin_client()
        url = reverse("admin:orders_order_changelist")
        data = {"action": "cancel_orders", "_selected_action": [order.pk]}
        admin.post(url, data)
        admin.post(url, data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.stock(), 10)

    def test_csv_export_contains_order_and_items(self):
        order = self.order_via_client()
        response = self.admin_client().post(
            reverse("admin:orders_order_changelist"),
            {"action": "export_orders_csv", "_selected_action": [order.pk]},
        )
        self.assertIn("text/csv", response["Content-Type"])
        content = response.content.decode("utf-8-sig")
        for expected in (order.reference, "Coque Pixel 8", "Noir", "12.00"):
            self.assertIn(expected, content)

    def test_checkout_request_expires_stale_unpaid_orders(self):
        order = self.order_via_client()
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=30))
        cache.delete("expire_orders_check")
        Client().get(reverse("orders:checkout"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.stock(), 10)

    def test_seed_initial_is_idempotent(self):
        call_command("seed_initial", stdout=io.StringIO())
        counts = (PixelModel.objects.count(), Category.objects.count(), DeliveryZone.objects.count())
        call_command("seed_initial", stdout=io.StringIO())
        self.assertEqual(
            counts, (PixelModel.objects.count(), Category.objects.count(), DeliveryZone.objects.count())
        )
        self.assertGreaterEqual(counts[0], 16)

    def test_security_audit_reports_issues(self):
        User.objects.create_user("agent", password=PASSWORD, is_staff=True)
        order = self.order_via_client()
        payment = order.payments.get()
        self.admin_client().post(
            reverse("admin:payments_payment_changelist"),
            {"action": "confirm_payments", "_selected_action": [payment.pk]},
        )
        Order.objects.filter(pk=order.pk).update(status=Order.Status.CANCELLED)
        out = io.StringIO()
        call_command("security_audit", stdout=out)
        text = out.getvalue()
        self.assertIn("agent", text)
        self.assertIn("remboursement", text)

    def test_revoke_sessions_targets_one_user(self):
        alice = User.objects.create_user("alice", password=PASSWORD)
        bob = User.objects.create_user("bob", password=PASSWORD)
        a, b = Client(), Client()
        a.force_login(alice)
        b.force_login(bob)
        self.assertEqual(Session.objects.count(), 2)
        call_command("revoke_sessions", user="alice", stdout=io.StringIO())
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(a.get(reverse("accounts:account")).status_code, 302)
        self.assertEqual(b.get(reverse("accounts:account")).status_code, 200)
        call_command("revoke_sessions", stdout=io.StringIO())
        self.assertEqual(Session.objects.count(), 0)

    def test_checkout_detects_stock_change_instead_of_shrinking_the_order(self):
        client = Client()
        self.add_to_cart(client, quantity=3)
        client.get(reverse("orders:checkout"))
        ProductVariant.objects.filter(pk=self.variant.pk).update(stock=1)
        response = client.post(reverse("orders:checkout"), self.payload(), follow=True)
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(response, "quantité")
        client.post(reverse("orders:checkout"), self.payload())
        order = Order.objects.get()
        self.assertEqual(order.items.get().quantity, 1)