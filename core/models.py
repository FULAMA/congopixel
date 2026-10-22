from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class SiteSettings(models.Model):
    store_name = models.CharField("nom de la boutique", max_length=80, default="CongoPixel")
    whatsapp_number = models.CharField(
        "numéro WhatsApp", max_length=20, blank=True,
        help_text="Format international sans + ni espaces, ex : 243XXXXXXXXX",
    )
    orange_money_number = models.CharField("numéro Orange Money", max_length=20, blank=True)
    mpesa_number = models.CharField("numéro M-Pesa", max_length=20, blank=True)
    orange_qr_image = models.ImageField("code QR Orange Money / Max it", upload_to="qr/", blank=True, help_text="Image du code QR marchand fournie par Orange (facultatif).")
    mpesa_qr_image = models.ImageField("code QR M-Pesa", upload_to="qr/", blank=True, help_text="Image du code QR marchand fournie par Vodacom (facultatif).")
    usd_to_cdf_rate = models.DecimalField(
        "taux : 1 USD en CDF", max_digits=10, decimal_places=2,
        default=Decimal("2800.00"), validators=[MinValueValidator(Decimal("1"))],
        help_text="Valeur provisoire : à régler selon le taux du jour.",
    )

    class Meta:
        verbose_name = "paramètres du site"
        verbose_name_plural = "paramètres du site"

    def __str__(self):
        return "Paramètres du site"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj