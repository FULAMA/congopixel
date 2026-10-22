from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("boutique/", views.product_list, name="product_list"),
    path("boutique/<slug:category_slug>/", views.product_list, name="category"),
    path("produit/<slug:slug>/", views.product_detail, name="product_detail"),
]