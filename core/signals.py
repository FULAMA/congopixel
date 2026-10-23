import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.dispatch import receiver

from .auth import WINDOW, failure_key

security_log = logging.getLogger("congopixel.security")


def _mask(value):
    value = str(value or "")
    return value[:1] + "***" + value[-2:] if len(value) > 4 else "***"


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    username = credentials.get("username") or ""
    if username:
        key = failure_key(username)
        cache.add(key, 0, WINDOW)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, WINDOW)
    security_log.warning("Échec de connexion (%s)", _mask(username))


@receiver(user_logged_in)
def on_logged_in(sender, request, user, **kwargs):
    cache.delete(failure_key(user.get_username()))
    if user.is_staff:
        security_log.info("Connexion équipe : %s", user.get_username())