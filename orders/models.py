import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalog.models import ProductVariant
from core.models import TimeStampedModel
from core.utils import usd_to_cdf


class DeliveryZone(models.Model):
    name = models.CharField("zone", max_length=80, unique=True)
    fee_usd = models.DecimalField(
        "frais de livraison (USD)", max_digits=7, decimal_places=2,
        default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0"))],
    )
    estimated_delay = models.CharField("délai estimé", max_length=60, blank=True, help_text="Ex : 24 h, 2 à 4 jours")
    position = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        ordering = ["position", "name"]
        verbose_name = "zone de livraison"
        verbose_name_plural = "zones de livraison"

    def __str__(self):
        return self.name


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "En attente de paiement"
        PAYMENT_SUBMITTED = "payment_submitted", "Paiement à vérifier"
        PAID = "paid", "Payée"
        PREPARING = "preparing", "En préparation"
        SHIPPED = "shipped", "Expédiée"
        DELIVERED = "delivered", "Livrée"
        CANCELLED = "cancelled", "Annulée"

    reference = models.CharField("référence", max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="orders", verbose_name="compte client",
    )
    full_name = models.CharField("nom complet", max_length=120)
    phone = models.CharField("téléphone", max_length=20)
    email = models.EmailField("e-mail", blank=True)
    city = models.CharField("ville", max_length=80)
    address = models.TextField("adresse de livraison")
    delivery_zone = models.ForeignKey(DeliveryZone, on_delete=models.PROTECT, verbose_name="zone de livraison")
    notes = models.TextField("remarques", blank=True)
    status = models.CharField("statut", max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    subtotal_usd = models.DecimalField("sous-total (USD)", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_usd = models.DecimalField("livraison (USD)", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_usd = models.DecimalField("total (USD)", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    exchange_rate = models.DecimalField("taux USD/CDF figé", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    stock_restored = models.BooleanField("stock remis", default=False, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "commande"
        verbose_name_plural = "commandes"

    def __str__(self):
        return self.reference

    @classmethod
    def generate_reference(cls):
        while True:
            ref = f"CP-{secrets.token_hex(3).upper()}"
            if not cls.objects.filter(reference=ref).exists():
                return ref

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)

    @property
    def total_cdf(self):
        return usd_to_cdf(self.total_usd, self.exchange_rate)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField("produit", max_length=160)
    variant_name = models.CharField("variante", max_length=80)
    unit_price_usd = models.DecimalField("prix unitaire (USD)", max_digits=8, decimal_places=2)
    quantity = models.PositiveSmallIntegerField("quantité", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "article commandé"
        verbose_name_plural = "articles commandés"

    def __str__(self):
        return f"{self.quantity} x {self.product_name} ({self.variant_name})"

    @property
    def line_total_usd(self):
        return self.unit_price_usd * self.quantity