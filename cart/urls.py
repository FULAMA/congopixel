from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("panier/", views.cart_detail, name="detail"),
    path("panier/ajouter/", views.cart_add, name="add"),
    path("panier/modifier/", views.cart_update, name="update"),
    path("panier/retirer/", views.cart_remove, name="remove"),
]