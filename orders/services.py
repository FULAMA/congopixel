from decimal import Decimal

from django.db import transaction
from django.db.models import F

from catalog.models import ProductVariant
from core.utils import get_rate
from payments.models import Payment

from .models import Order, OrderItem


class StockError(Exception):
    pass


@transaction.atomic
def create_order(cart, data, payment_method, user=None):
    lines = cart.lines()
    if not lines:
        raise StockError("Votre panier est vide.")

    locked = {
        v.pk: v
        for v in ProductVariant.objects.select_for_update().filter(pk__in=[l.variant.pk for l in lines])
    }

    items = []
    subtotal = Decimal("0.00")
    for line in lines:
        variant = locked.get(line.variant.pk)
        if variant is None or not variant.is_active or variant.stock < line.quantity:
            raise StockError(f"Stock insuffisant pour {line.variant.product.name} ({line.variant.name}).")
        price = variant.unit_price_usd
        subtotal += price * line.quantity
        items.append((variant, line.quantity, price))

    zone = data["delivery_zone"]
    order = Order.objects.create(
        user=user,
        full_name=data["full_name"],
        phone=data["phone"],
        email=data.get("email", ""),
        city=data["city"],
        address=data["address"],
        notes=data.get("notes", ""),
        delivery_zone=zone,
        subtotal_usd=subtotal,
        shipping_usd=zone.fee_usd,
        total_usd=subtotal + zone.fee_usd,
        exchange_rate=get_rate(),
    )
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order, variant=variant, product_name=variant.product.name,
            variant_name=variant.name, unit_price_usd=price, quantity=quantity,
        )
        for variant, quantity, price in items
    ])
    for variant, quantity, _ in items:
        ProductVariant.objects.filter(pk=variant.pk).update(stock=F("stock") - quantity)
    Payment.objects.create(order=order, method=payment_method, amount_usd=order.total_usd)
    return order

@transaction.atomic
def restock_order(order):
    """Remet en stock les articles d'une commande annulée, une seule fois."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.stock_restored:
        return False
    for item in order.items.all():
        ProductVariant.objects.filter(pk=item.variant_id).update(stock=F("stock") + item.quantity)
    order.stock_restored = True
    order.save(update_fields=["stock_restored", "updated_at"])
    return True