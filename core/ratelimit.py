from django.core.cache import cache


def is_limited(request, scope, limit, window):
    """Compte les actions d'une session ; retourne True si la limite est dépassée."""
    if not request.session.session_key:
        request.session.create()
    key = f"rl:{scope}:{request.session.session_key}"
    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        count = 1
    return count > limit