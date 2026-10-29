import io
import tempfile
from decimal import Decimal

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from PIL import Image

from .admin import ProductAdmin
from .models import Category, Product, ProductImage, ProductVariant


class ImageOptimizationTests(TestCase):
    def test_upload_is_resized_and_thumbnail_created(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            category = Category.objects.create(name="Coques", slug="coques")
            product = Product.objects.create(
                category=category, name="Coque", slug="coque", price_usd=Decimal("10.00")
            )
            buffer = io.BytesIO()
            Image.new("RGB", (3000, 2000), (20, 66, 108)).save(buffer, format="PNG")
            upload = SimpleUploadedFile("grande.png", buffer.getvalue(), content_type="image/png")
            photo = ProductImage.objects.create(product=product, image=upload)

            with Image.open(photo.image.path) as main:
                self.assertEqual(main.format, "WEBP")
                self.assertLessEqual(max(main.size), 1200)
            with Image.open(photo.thumb.path) as thumb:
                self.assertLessEqual(max(thumb.size), 480)
            self.assertIn("thumbs", photo.list_url)
            self.assertTrue(photo.list_url.endswith(".webp"))

class ConfigurableLowStockTests(TestCase):
    def test_admin_marks_variant_low_stock_using_its_configured_threshold(self):
        category = Category.objects.create(name="Accessoires", slug="accessoires")
        low_product = Product.objects.create(
            category=category, name="Chargeur", slug="chargeur", price_usd=Decimal("15.00")
        )
        normal_product = Product.objects.create(
            category=category, name="Cable", slug="cable", price_usd=Decimal("5.00")
        )
        ProductVariant.objects.create(
            product=low_product, name="Blanc", stock=4, low_stock_threshold=5
        )
        ProductVariant.objects.create(
            product=normal_product, name="Noir", stock=4, low_stock_threshold=3
        )

        queryset = ProductAdmin(Product, admin.site).get_queryset(
            RequestFactory().get("/admin/catalog/product/")
        )
        low = queryset.get(pk=low_product.pk)
        normal = queryset.get(pk=normal_product.pk)

        self.assertTrue(low.has_low_stock)
        self.assertEqual(low.total_stock, 4)
        self.assertFalse(normal.has_low_stock)

    def test_inactive_variants_do_not_trigger_low_stock_alert(self):
        category = Category.objects.create(name="Audio", slug="audio")
        product = Product.objects.create(
            category=category, name="Ecouteurs", slug="ecouteurs", price_usd=Decimal("20.00")
        )
        ProductVariant.objects.create(
            product=product, name="Noir", stock=1, low_stock_threshold=5, is_active=False
        )

        queryset = ProductAdmin(Product, admin.site).get_queryset(
            RequestFactory().get("/admin/catalog/product/")
        )
        self.assertFalse(queryset.get(pk=product.pk).has_low_stock)
