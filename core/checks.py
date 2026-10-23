from django.conf import settings
from django.core.checks import Error, Warning, register


@register(deploy=True)
def production_hardening_check(app_configs, **kwargs):
    problems = []
    if settings.ADMIN_URL == "admin/":
        problems.append(Warning(
            "L'adresse de l'admin est celle par défaut (admin/).",
            hint="Définissez ADMIN_URL dans le .env de production.", id="congopixel.W001",
        ))
    key = settings.SECRET_KEY
    if key.startswith("django-insecure") or len(key) < 40:
        problems.append(Error(
            "SECRET_KEY faible ou par défaut.",
            hint="Générez une nouvelle clé longue et aléatoire.", id="congopixel.E001",
        ))
    if "*" in settings.ALLOWED_HOSTS:
        problems.append(Error(
            "ALLOWED_HOSTS contient « * ».",
            hint="Listez uniquement vos vrais noms de domaine.", id="congopixel.E002",
        ))
    if not settings.CSRF_TRUSTED_ORIGINS:
        problems.append(Warning(
            "CSRF_TRUSTED_ORIGINS est vide.",
            hint="Ajoutez https://votre-domaine dans le .env de production.", id="congopixel.W002",
        ))
    return problems

@register(deploy=True)
def two_factor_check(app_configs, **kwargs):
    if getattr(settings, "ADMIN_2FA", False):
        return []
    return [Warning(
        "La double authentification de l'admin n'est pas activée.",
        hint="Créez un appareil avec « python manage.py setup_2fa NOM », puis ajoutez ADMIN_2FA=True au .env.",
        id="congopixel.W003",
    )]