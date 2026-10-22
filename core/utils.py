from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache

RATE_CACHE_KEY = "usd_to_cdf_rate"


def get_rate():
    rate = cache.get(RATE_CACHE_KEY)
    if rate is None:
        from core.models import SiteSettings

        rate = SiteSettings.load().usd_to_cdf_rate
        cache.set(RATE_CACHE_KEY, rate, 60)
    return Decimal(rate)


def usd_to_cdf(amount_usd, rate=None):
    if rate is None:
        rate = get_rate()
    return (Decimal(amount_usd) * Decimal(rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)