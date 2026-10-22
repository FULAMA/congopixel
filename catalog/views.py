import re
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from core.models import SiteSettings

from .models import Category, PixelModel, Product


def _active_products():
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
    )


def home(request):
    context = {
        "categories": Category.objects.filter(is_active=True),
        "featured": _active_products().filter(is_featured=True)[:8],
        "latest": _active_products()[:8],
    }
    return render(request, "catalog/home.html", context)


def product_list(request, category_slug=None):
    products = _active_products()
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=category)

    if "pixel" in request.GET:
        request.session["pixel"] = request.GET["pixel"][:60]
    selected_pixel = None
    pixel_slug = request.session.get("pixel", "")
    if pixel_slug:
        selected_pixel = PixelModel.objects.filter(slug=pixel_slug, is_active=True).first()
        if selected_pixel:
            products = products.filter(
                Q(compatible_models=selected_pixel) | Q(is_universal=True)
            ).distinct()

    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    page = Paginator(products, 12).get_page(request.GET.get("page"))
    context = {
        "category": category,
        "selected_pixel": selected_pixel,
        "query": query,
        "page": page,
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(_active_products(), slug=slug)
    related = _active_products().filter(category=product.category).exclude(pk=product.pk)[:4]
    number = re.sub(r"\D", "", SiteSettings.load().whatsapp_number)
    whatsapp_url = ""
    if number:
        text = f"Bonjour CongoPixel, je suis intéressé par : {product.name} - {request.build_absolute_uri()}"
        whatsapp_url = f"https://wa.me/{number}?text={quote(text)}"
    context = {"product": product, "related": related, "whatsapp_url": whatsapp_url}
    return render(request, "catalog/product_detail.html", context)