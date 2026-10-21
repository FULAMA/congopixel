from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from orders.models import Order


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        MPESA = "mpesa", "M-Pesa"
        CASH_ON_DELIVERY = "cash_on_delivery", "Paiement à la livraison"

    class Status(models.TextChoices):
        PENDING = "pending", "À vérifier"
        CONFIRMED = "confirmed", "Confirmé"
        REJECTED = "rejected", "Rejeté"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments", verbose_name="commande")
    method = models.CharField("moyen de paiement", max_length=20, choices=Method.choices)
    amount_usd = models.DecimalField("montant (USD)", max_digits=10, decimal_places=2)
    payer_phone = models.CharField("numéro du payeur", max_length=20, blank=True)
    transaction_id = models.CharField("ID de transaction", max_length=60, blank=True)
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.PENDING)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name="confirmé par",
    )
    confirmed_at = models.DateTimeField("confirmé le", null=True, blank=True)
    admin_note = models.TextField("note interne", blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
        constraints = [
            models.UniqueConstraint(
                fields=["method", "transaction_id"],
                condition=~models.Q(transaction_id=""),
                name="unique_transaction_id_per_method",
            )
        ]

    def __str__(self):
        return f"{self.order.reference} - {self.get_method_display()}"