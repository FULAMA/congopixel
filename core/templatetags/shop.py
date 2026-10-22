from decimal import Decimal, InvalidOperation

from django import template

from core.utils import usd_to_cdf

register = template.Library()


@register.filter
def usd(value):
    try:
        return f"{Decimal(value):.2f}".replace(".", ",") + " $"
    except (InvalidOperation, TypeError, ValueError):
        return ""


@register.filter
def cdf(value):
    try:
        return f"{int(usd_to_cdf(value)):,}".replace(",", " ") + " FC"
    except (InvalidOperation, TypeError, ValueError):
        return ""