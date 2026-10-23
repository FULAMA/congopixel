import io
import re
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.forms import modelform_factory
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import User
from catalog.models import Product, ProductImage, ProductVariant
from core.checks import production_hardening_check
from core.testing import PASSWORD, ShopTestCase
from orders.models import DeliveryZone, Order

EVIL = "<script>alert(1)</script>"
INLINE_SCRIPT = re.compile(r'<script(?![^>]*(?:\bsrc=|application/ld\+json))[^>]*>', re.I)


class SecurityTests(ShopTestCase):
    # ---------- en-têtes et contenu actif ----------
    def test_security_headers_on_public_pages(self):
        response = self.client.get(reverse("catalog:home"))
        csp = response["Content-Security-Policy"]
        for directive in ("script-src 'self'", "object-src 'none'", "frame-ancestors 'none'", "form-action 'self'"):
            self.assertIn(directive, csp)
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("Referrer-Policy", response)
        self.assertIn("Permissions-Policy", response)

    def test_csp_is_not_applied_to_admin(self):
        response = self.client.get("/" + settings.ADMIN_URL + "login/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Security-Policy", response)

    def test_pages_have_no_inline_executable_scripts(self):
        urls = [
            reverse("catalog:home"), reverse("catalog:product_list"),
            reverse("catalog:product_detail", args=[self.product.slug]),
            reverse("cart:detail"), reverse("accounts:login"),
            reverse("accounts:register"), reverse("core:about"),
        ]
        for url in urls:
            html = self.client.get(url).content.decode()
            self.assertIsNone(INLINE_SCRIPT.search(html), url)

    # ---------- injections ----------
    def test_user_controlled_text_is_escaped(self):
        product = Product.objects.create(category=self.category, name=EVIL, slug="evil", price_usd=Decimal("5.00"))
        ProductVariant.objects.create(product=product, name=EVIL, stock=5)
        for url in (
            reverse("catalog:home"), reverse("catalog:product_list"),
            reverse("catalog:product_detail", args=[product.slug]),
        ):
            html = self.client.get(url).content.decode()
            self.assertNotIn(EVIL, html, url)
            self.assertIn("&lt;script&gt;", html, url)

    def test_search_query_and_order_fields_are_escaped(self):
        response = self.client.get(reverse("catalog:product_list"), {"q": EVIL})
        self.assertNotContains(response, EVIL)
        self.assertContains(response, "&lt;script&gt;")
        client = Client()
        self.add_to_cart(client)
        client.post(reverse("orders:checkout"), self.payload(address=EVIL, full_name=EVIL))
        order = Order.objects.get()
        detail = client.get(reverse("orders:detail", args=[order.reference]))
        self.assertNotContains(detail, EVIL)
        self.assertContains(detail, "&lt;script&gt;")

    def test_sql_injection_attempts_are_harmless(self):
        before = Product.objects.count()
        attempts = [
            {"q": "' OR '1'='1"}, {"q": "'; DROP TABLE catalog_product; --"},
            {"pixel": "' OR 1=1 --"}, {"page": "1; DROP TABLE x"},
        ]
        for params in attempts:
            response = self.client.get(reverse("catalog:product_list"), params)
            self.assertEqual(response.status_code, 200, params)
        self.assertEqual(self.client.get("/boutique/%27%20OR%201%3D1/").status_code, 404)
        self.assertEqual(Product.objects.count(), before)

    def test_post_endpoints_require_csrf_token(self):
        strict = Client(enforce_csrf_checks=True)
        register = {
            "first_name": "A", "last_name": "B", "email": "", "phone": "0812345678",
            "password1": PASSWORD, "password2": PASSWORD,
        }
        targets = [
            ("cart:add", {"variant_id": self.variant.pk, "quantity": 1}),
            ("cart:update", {"variant_id": self.variant.pk, "quantity": 2}),
            ("cart:remove", {"variant_id": self.variant.pk}),
            ("orders:checkout", self.payload()),
            ("accounts:register", register),
            ("accounts:login", {"username": "0812345678", "password": PASSWORD}),
            ("accounts:logout", {}),
        ]
        for name, data in targets:
            self.assertEqual(strict.post(reverse(name), data).status_code, 403, name)

    # ---------- contrôle d'accès ----------
    def test_orders_are_isolated_between_sessions(self):
        owner = Client()
        order = self.order_via_client(owner)
        detail = reverse("orders:detail", args=[order.reference])
        payment = reverse("orders:payment", args=[order.reference])
        self.assertEqual(owner.get(detail).status_code, 200)
        self.assertEqual(owner.get(payment).status_code, 200)
        stranger = Client()
        self.assertEqual(stranger.get(detail).status_code, 404)
        self.assertEqual(stranger.get(payment).status_code, 404)
        forged = stranger.post(payment, {"transaction_id": "HACK123456", "payer_phone": "0812345678"})
        self.assertEqual(forged.status_code, 404)
        staff = Client()
        staff.force_login(User.objects.create_user("agent", password=PASSWORD, is_staff=True))
        self.assertEqual(staff.get(detail).status_code, 200)

    def test_customers_cannot_enter_admin(self):
        customer = User.objects.create_user("243899999999", phone="243899999999", password=PASSWORD)
        self.client.force_login(customer)
        response = self.client.get("/" + settings.ADMIN_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_order_manager_group_is_limited(self):
        call_command("setup_groups", stdout=io.StringIO())
        agent = User.objects.create_user("agent", password=PASSWORD, is_staff=True)
        agent.groups.add(Group.objects.get(name="Gestionnaire de commandes"))
        order = self.order_via_client(Client())
        client = Client()
        client.force_login(agent)
        self.assertEqual(client.get(reverse("admin:orders_order_changelist")).status_code, 200)
        self.assertEqual(client.get(reverse("admin:orders_order_delete", args=[order.pk])).status_code, 403)
        self.assertEqual(client.get(reverse("admin:catalog_product_changelist")).status_code, 403)
        self.assertEqual(client.get(reverse("admin:core_sitesettings_changelist")).status_code, 403)
        self.assertEqual(client.get(reverse("admin:accounts_user_changelist")).status_code, 403)

    def test_csv_export_requires_staff(self):
        order = self.order_via_client(Client())
        response = Client().post(
            reverse("admin:orders_order_changelist"),
            {"action": "export_orders_csv", "_selected_action": [order.pk]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("text/csv", response.get("Content-Type", ""))

    def test_registration_cannot_grant_privileges(self):
        self.client.post(reverse("accounts:register"), {
            "first_name": "A", "last_name": "B", "email": "", "phone": "0812345678",
            "password1": PASSWORD, "password2": PASSWORD,
            "is_staff": "on", "is_superuser": "on", "is_active": "on", "groups": "1",
        })
        user = User.objects.get(phone="243812345678")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    # ---------- authentification ----------
    def test_weak_passwords_are_rejected_and_hashes_are_stored(self):
        base = {"first_name": "A", "last_name": "B", "email": "", "phone": "0812345678"}
        weak = self.client.post(reverse("accounts:register"), {**base, "password1": "12345678", "password2": "12345678"})
        self.assertEqual(weak.status_code, 200)
        self.assertFalse(User.objects.filter(phone="243812345678").exists())
        self.client.post(reverse("accounts:register"), {**base, "password1": PASSWORD, "password2": PASSWORD})
        user = User.objects.get(phone="243812345678")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertNotIn(PASSWORD, user.password)

    def test_session_key_rotates_on_login(self):
        User.objects.create_user("243812345678", phone="243812345678", password=PASSWORD)
        self.add_to_cart()
        before = self.client.session.session_key
        self.client.post(reverse("accounts:login"), {"username": "0812345678", "password": PASSWORD})
        after = self.client.session.session_key
        self.assertTrue(before)
        self.assertNotEqual(before, after)

    def test_no_open_redirect_on_login_and_register(self):
        User.objects.create_user("243811111111", phone="243811111111", password=PASSWORD)
        for target in ("https://evil.example/", "//evil.example/", "javascript:alert(1)"):
            response = Client().post(
                reverse("accounts:login"),
                {"username": "0811111111", "password": PASSWORD, "next": target},
            )
            self.assertEqual(response.status_code, 302)
            self.assertNotIn("evil", response["Location"], target)
            self.assertNotIn("javascript", response["Location"], target)
        response = Client().post(reverse("accounts:register"), {
            "first_name": "A", "last_name": "B", "email": "", "phone": "0822222222",
            "password1": PASSWORD, "password2": PASSWORD, "next": "https://evil.example/",
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil", response["Location"])

    def test_admin_login_is_throttled(self):
        self.make_superuser("boss")
        for _ in range(10):
            self.assertFalse(self.client.login(username="boss", password="mauvais"))
        self.assertFalse(self.client.login(username="boss", password=PASSWORD))
        cache.clear()
        self.assertTrue(self.client.login(username="boss", password=PASSWORD))

    def test_failed_login_is_logged_without_full_identifier_or_password(self):
        with self.assertLogs("congopixel.security", level="WARNING") as captured:
            self.client.login(username="243812345678", password="secret-xyz-123")
        text = "\n".join(captured.output)
        self.assertNotIn("243812345678", text)
        self.assertNotIn("secret-xyz-123", text)
        self.assertIn("2***78", text)

    # ---------- manipulation de données ----------
    def test_price_and_status_tampering_is_ignored(self):
        client = Client()
        self.add_to_cart(client)
        client.post(reverse("orders:checkout"), self.payload(
            total_usd="0.01", subtotal_usd="0.01", shipping_usd="0",
            status="paid", exchange_rate="1", stock_restored="on",
        ))
        order = Order.objects.get()
        self.assertEqual(order.total_usd, Decimal("12.00"))
        self.assertEqual(order.shipping_usd, Decimal("2.00"))
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(order.exchange_rate, Decimal("2800.00"))
        self.assertFalse(order.stock_restored)

    def test_cart_input_abuse_is_harmless(self):
        url = reverse("cart:add")

        def quantity():
            return self.client.get(reverse("cart:detail")).context["lines"][0].quantity

        self.client.post(url, {"variant_id": self.variant.pk, "quantity": "-5"})
        self.assertEqual(quantity(), 1)
        self.client.post(url, {"variant_id": self.variant.pk, "quantity": "abc"})
        self.assertEqual(quantity(), 2)
        self.client.post(url, {"variant_id": self.variant.pk, "quantity": "9" * 5000})
        self.assertIn(quantity(), (3, 10))
        self.client.post(url, {"variant_id": self.variant.pk, "quantity": "1000000000"})
        self.assertEqual(quantity(), 10)
        self.assertEqual(self.client.post(url, {"variant_id": "abc", "quantity": 1}).status_code, 404)
        self.assertEqual(self.client.post(url, {"variant_id": 999999, "quantity": 1}).status_code, 404)
        ProductVariant.objects.filter(pk=self.variant_universal.pk).update(is_active=False)
        inactive = self.client.post(url, {"variant_id": self.variant_universal.pk, "quantity": 1})
        self.assertEqual(inactive.status_code, 404)

    def test_invalid_zone_and_payment_method_are_rejected(self):
        closed = DeliveryZone.objects.create(name="Fermée", fee_usd=Decimal("0"), is_active=False)
        client = Client()
        self.add_to_cart(client)
        responses = [
            client.post(reverse("orders:checkout"), self.payload(delivery_zone=closed.pk)),
            client.post(reverse("orders:checkout"), self.payload(payment_method="bitcoin")),
            client.post(reverse("orders:checkout"), self.payload(delivery_zone=99999)),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_replaying_someone_elses_checkout_key_is_refused(self):
        owner = Client()
        key = str(uuid.uuid4())
        self.add_to_cart(owner)
        owner.post(reverse("orders:checkout"), self.payload(idempotency_key=key))
        attacker = Client()
        self.add_to_cart(attacker)
        response = attacker.post(reverse("orders:checkout"), self.payload(idempotency_key=key))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Order.objects.count(), 1)

    def test_uploads_must_be_real_images(self):
        form_class = modelform_factory(ProductImage, fields=["image"])
        samples = [
            ("photo.jpg", b"ceci n'est pas une image"),
            ("logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'),
            ("shell.php", b"<?php echo 1; ?>"),
        ]
        for name, content in samples:
            form = form_class(files={"image": SimpleUploadedFile(name, content)})
            self.assertFalse(form.is_valid(), name)

    # ---------- fuites d'information ----------
    def test_checkout_logs_contain_no_personal_data(self):
        with self.assertLogs("congopixel", level="INFO") as captured:
            self.order_via_client(Client())
        text = "\n".join(captured.output)
        for private in ("Client Test", "243812345678", "0812345678", "Avenue Test"):
            self.assertNotIn(private, text)

    def test_error_pages_do_not_leak_internals(self):
        response = self.client.get("/page-inexistante/")
        self.assertEqual(response.status_code, 404)
        for leak in ("Traceback", "Using the URLconf", "DEBUG = True", "SECRET_KEY"):
            self.assertNotContains(response, leak, status_code=404)

    def test_admin_url_is_not_advertised(self):
        for url in ("/robots.txt", "/sitemap.xml"):
            self.assertNotContains(self.client.get(url), settings.ADMIN_URL.strip("/"))
        if settings.ADMIN_URL != "admin/":
            self.assertEqual(self.client.get("/admin/").status_code, 404)

    # ---------- configuration de production ----------
    def test_hardening_check_flags_weak_config(self):
        with override_settings(
            ADMIN_URL="admin/", SECRET_KEY="django-insecure-abc",
            ALLOWED_HOSTS=["*"], CSRF_TRUSTED_ORIGINS=[],
        ):
            ids = {message.id for message in production_hardening_check(None)}
        self.assertEqual(ids, {"congopixel.W001", "congopixel.E001", "congopixel.E002", "congopixel.W002"})

    def test_hardening_check_accepts_good_config(self):
        with override_settings(
            ADMIN_URL="gestion-k7x2/", SECRET_KEY="x" * 60,
            ALLOWED_HOSTS=["fulama.pythonanywhere.com"],
            CSRF_TRUSTED_ORIGINS=["https://fulama.pythonanywhere.com"],
        ):
            self.assertEqual(production_hardening_check(None), [])