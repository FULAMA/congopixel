from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("inscription/", views.register, name="register"),
    path("connexion/", views.CustomerLoginView.as_view(), name="login"),
    path("deconnexion/", LogoutView.as_view(), name="logout"),
    path("mon-compte/", views.account, name="account"),
]