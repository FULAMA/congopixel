from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.admin_2fa import apply_admin_2fa
from core.sitemaps import SITEMAPS

apply_admin_2fa(admin.site, settings.ADMIN_2FA)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("", include("core.urls")),
    path("", include("accounts.urls")),
    path("", include("cart.urls")),
    path("", include("orders.urls")),
    path("", include("catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)