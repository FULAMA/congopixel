from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from catalog.models import ProductVariant
from core.testing import PASSWORD, ShopTestCase
from orders.models import Order


class JourneyTests(ShopTestCase):
    def stock(self):
        return ProductVariant.objects.get(pk=self.variant.pk).stock

    def test_guest_purchase_with_mobile_money(self):
        client = Client()
        self.assertContains(client.get(reverse("catalog:home")), "Coque Pixel 8")
        found = client.get(reverse("catalog:product_list"), {"q": "universel"})
        self.assertContains(found, "Câble universel")
        self.assertNotContains(found, "Coque Pixel 8")
        detail = client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertContains(detail, "Ajouter au panier")

        client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": 1})
        cart = client.post(
            reverse("cart:update"), {"variant_id": self.variant.pk, "quantity": 3}, follow=True
        )
        self.assertContains(cart, "Coque Pixel 8")
        self.assertContains(cart, "30,00 $")

        self.assertContains(client.get(reverse("orders:checkout")), "Kinshasa - livraison")
        response = client.post(reverse("orders:checkout"), self.payload(), follow=True)
        order = Order.objects.get()
        self.assertEqual(order.total_usd, Decimal("32.00"))
        self.assertContains(response, "243810000000")
        self.assertContains(response, "32,00 $")

        proof = client.post(
            reverse("orders:payment", args=[order.reference]),
            {"transaction_id": "OM2026TEST1", "payer_phone": "0812345678"},
            follow=True,
        )
        self.assertContains(proof, "Nous vérifions votre paiement")
        self.assertContains(proof, "Paiement à vérifier")

        payment = order.payments.get()
        self.admin_client().post(
            reverse("admin:payments_payment_changelist"),
            {"action": "confirm_payments", "_selected_action": [payment.pk]},
        )
        final = client.get(reverse("orders:detail", args=[order.reference]))
        self.assertContains(final, "Payée")
        self.assertEqual(self.stock(), 7)

    def test_cash_on_delivery_journey(self):
        client = Client()
        self.add_to_cart(client)
        response = client.post(
            reverse("orders:checkout"), self.payload(payment_method="cash_on_delivery"), follow=True
        )
        self.assertContains(response, "Nous vous appelons pour la confirmer")
        self.assertContains(response, "En attente de paiement")
        self.assertNotContains(response, "Payer maintenant")

    def test_registered_customer_journey(self):
        client = Client()
        client.post(reverse("accounts:register"), {
            "first_name": "Jean", "last_name": "Mbala", "email": "", "phone": "0812345678",
            "password1": PASSWORD, "password2": PASSWORD,
        })
        self.add_to_cart(client)
        client.post(reverse("orders:checkout"), self.payload(payment_method="cash_on_delivery"))
        order = Order.objects.get()
        self.assertEqual(order.user.phone, "243812345678")
        self.assertContains(client.get(reverse("accounts:account")), order.reference)
        client.post(reverse("accounts:logout"))
        self.assertEqual(client.get(reverse("accounts:account")).status_code, 302)
        client.post(reverse("accounts:login"), {"username": "0812345678", "password": PASSWORD})
        self.assertContains(client.get(reverse("accounts:account")), order.reference)
        self.assertEqual(Client().get(reverse("orders:detail", args=[order.reference])).status_code, 404)

    def test_my_pixel_filter_journey(self):
        client = Client()
        filtered = client.get(reverse("catalog:product_list"), {"pixel": "pixel-9"})
        self.assertContains(filtered, "Coque Pixel 9")
        self.assertContains(filtered, "Câble universel")
        self.assertNotContains(filtered, "Coque Pixel 8")
        remembered = client.get(reverse("catalog:product_list"))
        self.assertNotContains(remembered, "Coque Pixel 8")
        cleared = client.get(reverse("catalog:product_list"), {"pixel": ""})
        self.assertContains(cleared, "Coque Pixel 8")

    def test_out_of_stock_journey(self):
        ProductVariant.objects.filter(pk=self.variant.pk).update(stock=0)
        client = Client()
        detail = client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertContains(detail, "momentanément épuisé")
        self.add_to_cart(client)
        cart = client.get(reverse("cart:detail"))
        self.assertContains(cart, "Cet article est épuisé")
        self.assertContains(cart, "Votre panier est vide")

    def test_unpaid_mobile_money_order_expires(self):
        client = Client()
        order = self.order_via_client(client)
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=25))
        cache.delete("expire_orders_check")
        client.get(reverse("orders:checkout"))
        page = client.get(reverse("orders:payment", args=[order.reference]), follow=True)
        self.assertContains(page, "annulée ou a expiré")
        self.assertEqual(self.stock(), 10)