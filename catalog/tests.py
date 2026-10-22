import io
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Category, Product, ProductImage


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