import json
from decimal import Decimal

from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from cart.cart import MAX_PER_LINE, Cart
from catalog.models import ProductVariant
from catalog.views import _jsonld_escape
from core.models import SiteSettings
from core.ratelimit import is_limited
from core.templatetags.shop import cdf, fc, usd
from core.testing import ShopTestCase
from core.utils import get_rate, usd_to_cdf
from core.validators import normalize_phone
from orders.admin import _safe_cell
from orders.models import Order


def make_request():
    request = RequestFactory().get("/")
    request.session = SessionStore()
    return request


class ValidatorTests(TestCase):
    def test_normalize_phone_valid(self):
        for raw in ["0812345678", "+243 81 234 5678", "00243812345678", "243812345678", "812345678", "(081) 234-5678"]:
            self.assertEqual(normalize_phone(raw), "243812345678", raw)

    def test_normalize_phone_invalid(self):
        for raw in ["", "123", "abc", "1" * 20]:
            with self.assertRaises(ValidationError):
                normalize_phone(raw)


class MoneyTests(ShopTestCase):
    def test_filters(self):
        self.assertEqual(usd(Decimal("12.5")), "12,50 $")
        self.assertEqual(usd("abc"), "")
        self.assertEqual(usd(None), "")
        self.assertEqual(fc(33600), "33 600 FC")
        self.assertEqual(cdf(Decimal("12")), "33 600 FC")

    def test_usd_to_cdf_rounding(self):
        self.assertEqual(usd_to_cdf(Decimal("0.01"), rate=Decimal("2850.50")), Decimal("29"))
        self.assertEqual(usd_to_cdf("10", rate=2800), Decimal("28000"))

    def test_rate_is_cached_then_refreshed(self):
        self.assertEqual(get_rate(), Decimal("2800.00"))
        SiteSettings.objects.filter(pk=1).update(usd_to_cdf_rate=Decimal("3000.00"))
        self.assertEqual(get_rate(), Decimal("2800.00"))
        cache.clear()
        self.assertEqual(get_rate(), Decimal("3000.00"))

    def test_site_settings_is_singleton(self):
        SiteSettings(store_name="Autre").save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        SiteSettings.load().delete()
        self.assertEqual(SiteSettings.objects.count(), 1)


class CartTests(ShopTestCase):
    def test_add_caps_and_totals(self):
        big = ProductVariant.objects.create(product=self.product, name="Stock large", stock=50)
        cart = Cart(make_request())
        self.assertEqual(cart.add(big, 99), MAX_PER_LINE)
        self.assertEqual(cart.add(self.variant, 3), 3)
        self.assertEqual(cart.count, MAX_PER_LINE + 3)
        self.assertEqual(cart.subtotal, Decimal("130.00"))
        cart.set_quantity(self.variant, 0)
        self.assertEqual(cart.count, MAX_PER_LINE)
        cart.remove(big.pk)
        self.assertEqual(cart.count, 0)

    def test_variant_price_and_inactive_variant(self):
        special = ProductVariant.objects.create(
            product=self.product, name="Édition", stock=5, price_usd=Decimal("8.00")
        )
        request = make_request()
        cart = Cart(request)
        cart.add(special, 2)
        line = cart.lines()[0]
        self.assertEqual(line.unit_price, Decimal("8.00"))
        self.assertEqual(line.total, Decimal("16.00"))
        ProductVariant.objects.filter(pk=special.pk).update(is_active=False)
        self.assertEqual(Cart(request).lines(), [])

    def test_sync_clamps_to_stock(self):
        request = make_request()
        Cart(request).add(self.variant, 5)
        ProductVariant.objects.filter(pk=self.variant.pk).update(stock=2)
        fresh = Cart(request)
        self.assertTrue(fresh.sync())
        self.assertEqual(fresh.count, 2)
        self.assertFalse(Cart(request).sync())


class HelperTests(ShopTestCase):
    def test_order_reference_format_and_uniqueness(self):
        refs = set()
        for _ in range(20):
            order = Order.objects.create(
                full_name="A", phone="243812345678", city="K", address="x", delivery_zone=self.zone
            )
            self.assertRegex(order.reference, r"^CP-[0-9A-F]{6}$")
            refs.add(order.reference)
        self.assertEqual(len(refs), 20)

    def test_product_and_variant_helpers(self):
        self.product.old_price_usd = Decimal("15.00")
        self.assertTrue(self.product.has_discount)
        self.product.old_price_usd = Decimal("10.00")
        self.assertFalse(self.product.has_discount)
        self.product.old_price_usd = None
        self.assertFalse(self.product.has_discount)
        self.assertEqual(self.variant.unit_price_usd, Decimal("10.00"))
        self.assertTrue(self.variant.in_stock)

    def test_rate_limiter(self):
        request = make_request()
        results = [is_limited(request, "t", limit=2, window=60) for _ in range(3)]
        self.assertEqual(results, [False, False, True])

    def test_csv_cell_sanitizer(self):
        self.assertEqual(_safe_cell("=1+1"), "'=1+1")
        for risky in ["+1", "-1", "@a"]:
            self.assertTrue(_safe_cell(risky).startswith("'"), risky)
        self.assertEqual(_safe_cell("Jean"), "Jean")
        self.assertEqual(_safe_cell(""), "")

    def test_jsonld_escape(self):
        data = {"name": "</script><img src=x onerror=alert(1)>&"}
        text = _jsonld_escape(data)
        for char in "<>&":
            self.assertNotIn(char, text)
        self.assertEqual(json.loads(text), data)