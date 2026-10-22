from django.contrib import admin, messages

from .models import Payment, PaymentEvent
from .services import ALREADY_CONFIRMED, CONFIRMED, NOT_PENDING, ORDER_CANCELLED, confirm_payment

RESULT_LABELS = {
    CONFIRMED: "confirmé(s)",
    ALREADY_CONFIRMED: "déjà confirmé(s)",
    NOT_PENDING: "ignoré(s) (statut différent de « à vérifier »)",
    ORDER_CANCELLED: "bloqué(s) car la commande est annulée : remboursement ou nouvelle commande à traiter à la main",
}


@admin.action(description="Confirmer les paiements Mobile Money sélectionnés")
def confirm_payments(modeladmin, request, queryset):
    results = {}
    for payment in queryset.exclude(method=Payment.Method.CASH_ON_DELIVERY):
        result = confirm_payment(payment.pk, confirmed_by=request.user)
        results[result] = results.get(result, 0) + 1
    parts = [f"{count} paiement(s) {RESULT_LABELS[result]}" for result, count in results.items()]
    level = messages.WARNING if ORDER_CANCELLED in results else messages.SUCCESS
    modeladmin.message_user(request, " ; ".join(parts) or "Rien à confirmer.", level)


@admin.action(description="Rejeter les paiements sélectionnés")
def reject_payments(modeladmin, request, queryset):
    queryset.filter(status=Payment.Status.PENDING).update(status=Payment.Status.REJECTED)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "amount_usd", "transaction_id", "payer_phone", "status", "created_at")
    list_filter = ("status", "method")
    search_fields = ("order__reference", "transaction_id", "payer_phone")
    readonly_fields = ("status", "confirmed_by", "confirmed_at", "created_at", "updated_at")
    actions = [confirm_payments, reject_payments]


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "provider", "event_id", "order_reference", "success", "outcome")
    list_filter = ("provider", "outcome")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False