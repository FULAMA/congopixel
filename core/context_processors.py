import re

from catalog.models import Category, PixelModel
from core.models import SiteSettings


def site(request):
    settings_obj = SiteSettings.load()
    return {
        "site": settings_obj,
        "whatsapp_digits": re.sub(r"\D", "", settings_obj.whatsapp_number),
        "nav_categories": Category.objects.filter(is_active=True),
        "pixel_models": PixelModel.objects.filter(is_active=True),
        "selected_pixel_slug": request.session.get("pixel", ""),
    }