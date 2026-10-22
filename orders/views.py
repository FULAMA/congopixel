import logging

from django.contrib import messages
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from cart.cart import Cart
from core.models import SiteSettings
from core.ratelimit import is_limited
from payments.forms import MobileMoneyProofForm
from payments.models import Payment

from .access import can_view_order, remember_order
from .forms import CheckoutForm
from .models import Order
from .services import StockError, create_order, expire_stale_orders

logger = logging.getLogger("congopixel")
LIMIT_MESSAGE = "Trop de demandes en peu de temps. Réessayez dans un moment ou écrivez-nous sur WhatsApp."


def _get_order_or_404(request, reference):
    order = get_object_or_404(
        Order.objects.select_related("delivery_zone").prefetch_related("items", "payments"),
        reference=reference,
    )
    if not can_view_order(request, order):
        raise Http404
    return order


def checkout(request):
    if cache.add("expire_orders_check", 1, 600):
        expire_stale_orders()

    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, "Votre panier est vide.")
        return redirect("cart:detail")

    initial = {}
    if request.user.is_authenticated:
        initial = {
            "full_name": request.user.get_full_name(),
            "phone": request.user.phone or "",
            "email": request.user.email,
        }
    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        if is_limited(request, "checkout", limit=5, window=3600):
            messages.error(request, LIMIT_MESSAGE)
            return redirect("cart:detail")
        method = form.cleaned_data["payment_method"]
        try:
            order = create_order(
                cart, form.cleaned_data, method,
                user=request.user if request.user.is_authenticated else None,
            )
        except StockError as exc:
            messages.error(request, str(exc))
            return redirect("cart:detail")
        cart.clear()
        remember_order(request, order)
        if method == Payment.Method.CASH_ON_DELIVERY:
            messages.success(request, "Commande enregistrée. Nous vous appelons pour la confirmer.")
            return redirect("orders:detail", reference=order.reference)
        return redirect("orders:payment", reference=order.reference)

    return render(request, "orders/checkout.html", {"form": form, "cart_lines": lines, "subtotal": cart.subtotal})


def order_detail(request, reference):
    order = _get_order_or_404(request, reference)
    return render(request, "orders/order_detail.html", {"order": order})


def order_payment(request, reference):
    order = _get_order_or_404(request, reference)
    if order.status == Order.Status.CANCELLED:
        messages.error(
            request,
            "Cette commande a été annulée ou a expiré. Écrivez-nous sur WhatsApp si vous avez déjà payé.",
        )
        return redirect("orders:detail", reference=order.reference)

    payment = order.payments.order_by("-created_at", "-id").first()
    if (
        payment is None
        or payment.method == Payment.Method.CASH_ON_DELIVERY
        or payment.status == Payment.Status.CONFIRMED
    ):
        return redirect("orders:detail", reference=order.reference)

    site_settings = SiteSettings.load()
    if payment.method == Payment.Method.ORANGE_MONEY:
        pay_number = site_settings.orange_money_number
    else:
        pay_number = site_settings.mpesa_number

    awaiting_proof = (not payment.transaction_id) or payment.status == Payment.Status.REJECTED
    form = None
    if awaiting_proof:
        form = MobileMoneyProofForm(request.POST or None, payment=payment)
        if request.method == "POST" and form.is_valid():
            if is_limited(request, "payment_proof", limit=15, window=3600):
                messages.error(request, LIMIT_MESSAGE)
                return redirect("orders:detail", reference=order.reference)
            payment.transaction_id = form.cleaned_data["transaction_id"]
            payment.payer_phone = form.cleaned_data["payer_phone"]
            payment.status = Payment.Status.PENDING
            try:
                with transaction.atomic():
                    payment.save()
            except IntegrityError:
                form.add_error("transaction_id", "Cet ID de transaction a déjà été utilisé.")
            else:
                order.status = Order.Status.PAYMENT_SUBMITTED
                order.save(update_fields=["status", "updated_at"])
                logger.info("Preuve de paiement reçue pour %s (%s)", order.reference, payment.method)
                messages.success(request, "Merci ! Nous vérifions votre paiement et vous contactons très vite.")
                return redirect("orders:detail", reference=order.reference)

    context = {"order": order, "payment": payment, "pay_number": pay_number, "form": form}
    return render(request, "orders/payment.html", context)