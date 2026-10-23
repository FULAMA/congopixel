from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import ProductVariant

from .cart import Cart


def _variant_from_post(request):
    try:
        pk = int(request.POST.get("variant_id", ""))
    except ValueError:
        raise Http404
    return get_object_or_404(ProductVariant, pk=pk, is_active=True, product__is_active=True)


def _quantity_from_post(request):
    try:
        return int(request.POST.get("quantity", "1"))
    except ValueError:
        return 1


def cart_detail(request):
    cart = Cart(request)
    if cart.sync():
        messages.warning(request, "Certaines quantités ont été ajustées au stock disponible.")
    return render(request, "cart/detail.html", {"lines": cart.lines(), "subtotal": cart.subtotal})


@require_POST
def cart_add(request):
    variant = _variant_from_post(request)
    if variant.stock <= 0:
        messages.error(request, "Cet article est épuisé.")
    else:
        Cart(request).add(variant, max(1, _quantity_from_post(request)))
        messages.success(request, "Ajouté au panier.")
    return redirect("cart:detail")


@require_POST
def cart_update(request):
    variant = _variant_from_post(request)
    Cart(request).set_quantity(variant, _quantity_from_post(request))
    return redirect("cart:detail")


@require_POST
def cart_remove(request):
    Cart(request).remove(request.POST.get("variant_id", ""))
    return redirect("cart:detail")