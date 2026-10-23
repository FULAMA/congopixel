from collections import namedtuple
from decimal import Decimal

from catalog.models import ProductVariant

CART_SESSION_KEY = "cart"
MAX_PER_LINE = 10

CartLine = namedtuple("CartLine", ["variant", "quantity", "unit_price", "total"])


class Cart:
    def __init__(self, request):
        self.session = request.session
        self._data = self.session.get(CART_SESSION_KEY, {})
        self._lines = None

    def _save(self):
        self.session[CART_SESSION_KEY] = self._data
        self.session.modified = True
        self._lines = None

    def set_quantity(self, variant, quantity):
        quantity = max(0, min(int(quantity), variant.stock, MAX_PER_LINE))
        key = str(variant.pk)
        if quantity == 0:
            self._data.pop(key, None)
        else:
            self._data[key] = quantity
        self._save()
        return quantity

    def add(self, variant, quantity=1):
        current = self._data.get(str(variant.pk), 0)
        return self.set_quantity(variant, current + int(quantity))

    def remove(self, variant_id):
        self._data.pop(str(variant_id), None)
        self._save()

    def clear(self):
        self._data = {}
        self.session.pop(CART_SESSION_KEY, None)
        self.session.modified = True
        self._lines = None

    def lines(self):
        if self._lines is None:
            variants = (
                ProductVariant.objects.filter(
                    pk__in=list(self._data.keys()), is_active=True, product__is_active=True
                )
                .select_related("product")
                .prefetch_related("product__images")
            )
            lines = []
            for variant in variants:
                quantity = min(self._data.get(str(variant.pk), 0), variant.stock)
                if quantity > 0:
                    price = variant.unit_price_usd
                    lines.append(CartLine(variant, quantity, price, price * quantity))
            self._lines = lines
        return self._lines

    def sync(self):
        """Recale le panier sur le stock réel ; retourne True si quelque chose a changé."""
        cleaned = {str(line.variant.pk): line.quantity for line in self.lines()}
        changed = cleaned != self._data
        if changed:
            self._data = cleaned
            self._save()
        return changed

    @property
    def subtotal(self):
        return sum((line.total for line in self.lines()), Decimal("0.00"))

    @property
    def count(self):
        return sum(self._data.values())