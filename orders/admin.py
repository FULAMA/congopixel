from django.contrib import admin

from .models import DeliveryZone, Order, OrderItem
from .services import restock_order


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("variant", "product_name", "variant_name", "unit_price_usd", "quantity")

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description="Annuler les commandes sélectionnées et remettre le stock")
def cancel_orders(modeladmin, request, queryset):
    count = 0
    for order in queryset.exclude(status=Order.Status.DELIVERED):
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        if restock_order(order):
            count += 1
    modeladmin.message_user(request, f"{count} commande(s) annulée(s), stock remis.")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "full_name", "phone", "delivery_zone", "total_usd", "status", "created_at")
    list_filter = ("status", "delivery_zone")
    search_fields = ("reference", "full_name", "phone")
    readonly_fields = (
        "reference", "subtotal_usd", "shipping_usd", "total_usd",
        "exchange_rate", "stock_restored", "created_at", "updated_at",
    )
    inlines = [OrderItemInline]
    actions = [cancel_orders]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and obj.status == Order.Status.CANCELLED and restock_order(obj):
            self.message_user(request, "Commande annulée : le stock a été remis.")


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "fee_usd", "estimated_delay", "is_active")