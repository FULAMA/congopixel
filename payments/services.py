import logging
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone

from orders.models import Order

from .models import Payment, PaymentEvent

logger = logging.getLogger("congopixel")

CONFIRMED = "confirmed"
ALREADY_CONFIRMED = "already_confirmed"
NOT_PENDING = "not_pending"
ORDER_CANCELLED = "order_cancelled"
DUPLICATE = "duplicate"


@transaction.atomic
def confirm_payment(payment_id, confirmed_by=None):
    """Confirme un paiement une seule fois ; refuse si la commande est annulée."""
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if payment.status == Payment.Status.CONFIRMED:
        return ALREADY_CONFIRMED
    if payment.status != Payment.Status.PENDING:
        return NOT_PENDING
    order = Order.objects.select_for_update().get(pk=payment.order_id)
    if order.status == Order.Status.CANCELLED:
        logger.warning(
            "Paiement %s reçu pour la commande annulée %s : traitement manuel requis",
            payment.pk, order.reference,
        )
        return ORDER_CANCELLED
    payment.status = Payment.Status.CONFIRMED
    payment.confirmed_by = confirmed_by
    payment.confirmed_at = timezone.now()
    payment.save()
    if order.status in (Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_SUBMITTED):
        order.status = Order.Status.PAID
        order.save(update_fields=["status", "updated_at"])
    logger.info("Paiement confirmé pour %s", order.reference)
    return CONFIRMED


def _apply_event(order_reference, amount, currency, success):
    order = Order.objects.filter(reference=order_reference).first()
    if order is None:
        return "unknown_order"
    if not success:
        return "provider_failed"
    if currency == "USD":
        expected = order.total_usd
    elif currency == "CDF":
        expected = order.total_cdf
    else:
        return "unsupported_currency"
    try:
        paid = Decimal(str(amount))
    except InvalidOperation:
        return "invalid_amount"
    if paid != Decimal(expected):
        return "amount_mismatch"
    if order.payments.filter(status=Payment.Status.CONFIRMED).exists():
        return ALREADY_CONFIRMED
    payment = (
        order.payments.filter(
            status=Payment.Status.PENDING,
            method__in=[Payment.Method.ORANGE_MONEY, Payment.Method.MPESA],
        )
        .order_by("-id")
        .first()
    )
    if payment is None:
        return "no_pending_payment"
    return confirm_payment(payment.pk)


def record_provider_event(provider, event_id, order_reference, amount, currency, success):
    """Traite une notification d'un fournisseur de paiement, une seule fois par événement.

    Si le traitement échoue, rien n'est enregistré : le fournisseur pourra renvoyer l'événement.
    """
    if not event_id:
        raise ValueError("event_id obligatoire")
    with transaction.atomic():
        try:
            with transaction.atomic():
                event = PaymentEvent.objects.create(
                    provider=provider, event_id=event_id,
                    order_reference=order_reference, success=bool(success),
                )
        except IntegrityError:
            return DUPLICATE
        outcome = _apply_event(order_reference, amount, currency, success)
        event.outcome = outcome
        event.save(update_fields=["outcome"])
    logger.info("Événement %s/%s traité : %s", provider, event_id, outcome)
    return outcome