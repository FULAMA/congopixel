from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("livraison-et-retours/", views.shipping_returns, name="shipping_returns"),
    path("conditions-de-vente/", views.terms, name="terms"),
    path("a-propos/", views.about, name="about"),
    path("robots.txt", views.robots_txt, name="robots"),
]