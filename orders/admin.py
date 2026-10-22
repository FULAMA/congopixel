import csv
from urllib.parse import quote

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import DeliveryZone, Order, OrderItem
from .services import restock_order


def _safe_cell(value):
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


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


@admin.action(description="Exporter les commandes sélectionnées (CSV)")
def export_orders_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="commandes-congopixel.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Référence", "Date", "Statut", "Client", "Téléphone", "Ville", "Adresse",
        "Zone", "Articles", "Sous-total USD", "Livraison USD", "Total USD",
    ])
    for order in queryset.select_related("delivery_zone").prefetch_related("items"):
        articles = " | ".join(
            f"{i.quantity}x {i.product_name} ({i.variant_name})" for i in order.items.all()
        )
        writer.writerow([
            _safe_cell(order.reference),
            timezone.localtime(order.created_at).strftime("%d/%m/%Y %H:%M"),
            _safe_cell(order.get_status_display()),
            _safe_cell(order.full_name),
            _safe_cell(order.phone),
            _safe_cell(order.city),
            _safe_cell(order.address),
            _safe_cell(order.delivery_zone.name),
            _safe_cell(articles),
            order.subtotal_usd,
            order.shipping_usd,
            order.total_usd,
        ])
    return response


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "full_name", "phone", "delivery_zone", "total_usd", "status", "created_at", "contact")
    list_filter = ("status", "delivery_zone")
    search_fields = ("reference", "full_name", "phone")
    readonly_fields = (
        "reference", "subtotal_usd", "shipping_usd", "total_usd",
        "exchange_rate", "stock_restored", "created_at", "updated_at", "contact",
    )
    inlines = [OrderItemInline]
    actions = [cancel_orders, export_orders_csv]

    @admin.display(description="Contact")
    def contact(self, obj):
        text = quote(f"Bonjour {obj.full_name}, c'est CongoPixel au sujet de votre commande {obj.reference}.")
        return format_html(
            '<a href="https://wa.me/{}?text={}" target="_blank" rel="noopener">WhatsApp</a>', obj.phone, text
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and obj.status == Order.Status.CANCELLED and restock_order(obj):
            self.message_user(request, "Commande annulée : le stock a été remis.")


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "fee_usd", "estimated_delay", "is_active")