from decimal import Decimal

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Category, Product, ProductVariant
from orders.models import DeliveryZone, Order

from .models import User

PASSWORD = "Mot-de-passe-solide-42"


class AccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def register(self, client=None, phone="0812345678"):
        return (client or self.client).post(reverse("accounts:register"), {
            "first_name": "Jean", "last_name": "Mbala", "email": "",
            "phone": phone, "password1": PASSWORD, "password2": PASSWORD,
        })

    def test_register_creates_user_and_logs_in(self):
        response = self.register()
        self.assertRedirects(response, reverse("accounts:account"))
        user = User.objects.get(phone="243812345678")
        self.assertEqual(user.username, "243812345678")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_phone_is_rejected(self):
        self.register()
        response = self.register(Client(), phone="+243 81 234 5678")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_login_with_local_phone_format(self):
        self.register()
        self.client.post(reverse("accounts:logout"))
        response = self.client.post(reverse("accounts:login"), {"username": "0812345678", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:account"))

    def test_login_is_throttled_after_repeated_failures(self):
        self.register()
        self.client.post(reverse("accounts:logout"))
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "0812345678", "password": "mauvais"})
        response = self.client.post(reverse("accounts:login"), {"username": "0812345678", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_account_requires_login(self):
        response = self.client.get(reverse("accounts:account"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_logged_in_checkout_links_order_to_account(self):
        category = Category.objects.create(name="Coques", slug="coques")
        product = Product.objects.create(category=category, name="Coque", slug="coque", price_usd=Decimal("10.00"))
        variant = ProductVariant.objects.create(product=product, name="Noir", stock=5)
        zone = DeliveryZone.objects.create(name="Kinshasa", fee_usd=Decimal("2.00"))
        self.register()
        self.client.post(reverse("cart:add"), {"variant_id": variant.pk, "quantity": 1})
        self.client.post(reverse("orders:checkout"), {
            "full_name": "Jean Mbala", "phone": "0812345678", "email": "", "city": "Kinshasa",
            "address": "Avenue Test 1", "delivery_zone": zone.pk, "notes": "", "payment_method": "cash_on_delivery",
        })
        order = Order.objects.get()
        self.assertEqual(order.user.phone, "243812345678")
        response = self.client.get(reverse("accounts:account"))
        self.assertContains(response, order.reference)