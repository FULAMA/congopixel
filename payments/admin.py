from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from orders.models import Order

from .models import Payment


@admin.action(description="Confirmer les paiements Mobile Money sélectionnés")
def confirm_payments(modeladmin, request, queryset):
    pending = (
        queryset.filter(status=Payment.Status.PENDING)
        .exclude(method=Payment.Method.CASH_ON_DELIVERY)
        .select_related("order")
    )
    with transaction.atomic():
        for payment in pending:
            payment.status = Payment.Status.CONFIRMED
            payment.confirmed_by = request.user
            payment.confirmed_at = timezone.now()
            payment.save()
            payment.order.status = Order.Status.PAID
            payment.order.save(update_fields=["status", "updated_at"])


@admin.action(description="Rejeter les paiements sélectionnés")
def reject_payments(modeladmin, request, queryset):
    queryset.filter(status=Payment.Status.PENDING).update(status=Payment.Status.REJECTED)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "amount_usd", "transaction_id", "payer_phone", "status", "created_at")
    list_filter = ("status", "method")
    search_fields = ("order__reference", "transaction_id", "payer_phone")
    readonly_fields = ("confirmed_by", "confirmed_at", "created_at", "updated_at")
    actions = [confirm_payments, reject_payments]