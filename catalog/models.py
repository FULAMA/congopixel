from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.models import TimeStampedModel
from core.utils import usd_to_cdf

from .images import optimize


class PixelModel(models.Model):
    name = models.CharField("modèle", max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    release_year = models.PositiveSmallIntegerField("année de sortie", null=True, blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ["-release_year", "name"]
        verbose_name = "modèle Pixel"
        verbose_name_plural = "modèles Pixel"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("nom", max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    image = models.ImageField("image", upload_to="categories/", blank=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        ordering = ["position", "name"]
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="catégorie")
    name = models.CharField("nom", max_length=160)
    slug = models.SlugField(unique=True)
    description = models.TextField("description", blank=True)
    price_usd = models.DecimalField(
        "prix (USD)", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    old_price_usd = models.DecimalField(
        "ancien prix (USD)", max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Renseigner pour afficher une promotion.",
    )
    compatible_models = models.ManyToManyField(
        PixelModel, blank=True, related_name="accessories", verbose_name="modèles Pixel compatibles"
    )
    is_universal = models.BooleanField(
        "universel", default=False, help_text="Compatible avec tous les smartphones."
    )
    is_active = models.BooleanField("actif", default=True)
    is_featured = models.BooleanField("mis en avant", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "produit"
        verbose_name_plural = "produits"

    def __str__(self):
        return self.name

    @property
    def price_cdf(self):
        return usd_to_cdf(self.price_usd)

    @property
    def has_discount(self):
        return bool(self.old_price_usd and self.old_price_usd > self.price_usd)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("image", upload_to="products/%Y/%m/")
    thumb = models.ImageField("miniature", upload_to="products/thumbs/%Y/%m/", blank=True, editable=False)
    alt = models.CharField("texte alternatif", max_length=160, blank=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "image du produit"
        verbose_name_plural = "images du produit"

    def __str__(self):
        return f"Image de {self.product}"

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            optimize(self)
        super().save(*args, **kwargs)

    @property
    def list_url(self):
        return (self.thumb or self.image).url


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField("variante", max_length=80, help_text="Ex : Noir, 1 m, 30 W, Standard")
    sku = models.CharField("référence", max_length=40, unique=True, null=True, blank=True)
    price_usd = models.DecimalField(
        "prix spécifique (USD)", max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Laisser vide pour utiliser le prix du produit.",
    )
    stock = models.PositiveIntegerField("stock", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "variante"
        verbose_name_plural = "variantes"
        constraints = [
            models.UniqueConstraint(fields=["product", "name"], name="unique_variant_name_per_product")
        ]

    def __str__(self):
        return f"{self.product} - {self.name}"

    @property
    def unit_price_usd(self):
        return self.price_usd if self.price_usd is not None else self.product.price_usd

    @property
    def in_stock(self):
        return self.is_active and self.stock > 0