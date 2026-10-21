from decimal import ROUND_HALF_UP, Decimal


def usd_to_cdf(amount_usd, rate=None):
    if rate is None:
        from core.models import SiteSettings

        rate = SiteSettings.load().usd_to_cdf_rate
    return (Decimal(amount_usd) * Decimal(rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)