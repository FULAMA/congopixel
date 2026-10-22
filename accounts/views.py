from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import PhoneLoginForm, RegisterForm


class CustomerLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = PhoneLoginForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        next_url = request.POST.get("next") or request.GET.get("next") or ""
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect("accounts:account")
    return render(request, "accounts/register.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
def account(request):
    orders = request.user.orders.select_related("delivery_zone")
    return render(request, "accounts/account.html", {"orders": orders})