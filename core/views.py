from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from orders.models import DeliveryZone


def shipping_returns(request):
    zones = DeliveryZone.objects.filter(is_active=True)
    return render(request, "core/shipping_returns.html", {"zones": zones})


def terms(request):
    return render(request, "core/terms.html")


def about(request):
    return render(request, "core/about.html")


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /panier/",
        "Disallow: /commander/",
        "Disallow: /commande/",
        "Disallow: /mon-compte/",
        "Disallow: /connexion/",
        "Disallow: /inscription/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")