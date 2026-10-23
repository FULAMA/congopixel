from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache

MAX_FAILURES = 10
WINDOW = 15 * 60


def failure_key(username):
    return f"authfail:{str(username).lower()}"


class ThrottledModelBackend(ModelBackend):
    """Bloque temporairement un identifiant après trop d'échecs (admin compris)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username and cache.get(failure_key(username), 0) >= MAX_FAILURES:
            return None
        return super().authenticate(request, username=username, password=password, **kwargs)