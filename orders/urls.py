from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("commander/", views.checkout, name="checkout"),
    path("commande/<str:reference>/", views.order_detail, name="detail"),
    path("commande/<str:reference>/paiement/", views.order_payment, name="payment"),
]