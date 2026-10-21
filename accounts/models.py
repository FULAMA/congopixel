from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField("téléphone", max_length=20, unique=True, null=True, blank=True)
    preferred_language = models.CharField(
        "langue préférée", max_length=5, default="fr",
        choices=[("fr", "Français"), ("en", "English"), ("ln", "Lingála")],
    )