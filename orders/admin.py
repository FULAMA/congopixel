from django.contrib import admin

from .models import DeliveryZone, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("variant", "product_name", "variant_name", "unit_price_usd", "quantity")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "full_name", "phone", "delivery_zone", "total_usd", "status", "created_at")
    list_filter = ("status", "delivery_zone")
    search_fields = ("reference", "full_name", "phone")
    readonly_fields = (
        "reference", "subtotal_usd", "shipping_usd", "total_usd",
        "exchange_rate", "created_at", "updated_at",
    )
    inlines = [OrderItemInline]


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "fee_usd", "estimated_delay", "is_active")