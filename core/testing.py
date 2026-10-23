import uuid
from decimal import Decimal

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from catalog.models import Category, PixelModel, Product, ProductVariant
from core.models import SiteSettings
from orders.models import DeliveryZone, Order

PASSWORD = "Mot-de-passe-solide-42"


class ShopTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = SiteSettings.load()
        site.usd_to_cdf_rate = Decimal("2800.00")
        site.orange_money_number = "243810000000"
        site.mpesa_number = "243820000000"
        site.whatsapp_number = "243830000000"
        site.save()
        cls.category = Category.objects.create(name="Coques", slug="coques")
        cls.pixel8 = PixelModel.objects.create(name="Pixel 8", slug="pixel-8", release_year=2023)
        cls.pixel9 = PixelModel.objects.create(name="Pixel 9", slug="pixel-9", release_year=2024)
        cls.product = Product.objects.create(
            category=cls.category, name="Coque Pixel 8", slug="coque-pixel-8", price_usd=Decimal("10.00")
        )
        cls.product.compatible_models.add(cls.pixel8)
        cls.variant = ProductVariant.objects.create(product=cls.product, name="Noir", stock=10)
        cls.case9 = Product.objects.create(
            category=cls.category, name="Coque Pixel 9", slug="coque-pixel-9", price_usd=Decimal("12.00")
        )
        cls.case9.compatible_models.add(cls.pixel9)
        cls.variant9 = ProductVariant.objects.create(product=cls.case9, name="Bleu", stock=3)
        cls.universal = Product.objects.create(
            category=cls.category, name="Câble universel", slug="cable-universel",
            price_usd=Decimal("5.00"), is_universal=True,
        )
        cls.variant_universal = ProductVariant.objects.create(product=cls.universal, name="1 m", stock=10)
        cls.zone = DeliveryZone.objects.create(name="Kinshasa", fee_usd=Decimal("2.00"), estimated_delay="24 h")

    def setUp(self):
        cache.clear()
        self.client = Client()

    def add_to_cart(self, client=None, variant=None, quantity=1):
        return (client or self.client).post(
            reverse("cart:add"), {"variant_id": (variant or self.variant).pk, "quantity": quantity}
        )

    def payload(self, **overrides):
        data = {
            "full_name": "Client Test", "phone": "0812345678", "email": "",
            "city": "Kinshasa", "address": "Avenue Test 1",
            "delivery_zone": self.zone.pk, "notes": "", "payment_method": "orange_money",
            "idempotency_key": str(uuid.uuid4()),
        }
        data.update(overrides)
        return data

    def order_via_client(self, client=None, method="orange_money", **overrides):
        client = client or Client()
        self.add_to_cart(client)
        client.post(reverse("orders:checkout"), self.payload(payment_method=method, **overrides))
        return Order.objects.order_by("-id").first()

    def make_superuser(self, username="boss"):
        return User.objects.create_superuser(username, password=PASSWORD)

    def admin_client(self):
        client = Client()
        client.force_login(self.make_superuser())
        return client