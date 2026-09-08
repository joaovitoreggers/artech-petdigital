"""Login attempt throttling for the PIN login screen.

A 6-digit PIN has only a million possible values, so unlike a hashed
password there's no expensive-to-compute hash slowing down guesses — the
defense here is capping how many attempts a client gets, not how long each
attempt takes.

Uses Django's default cache, which is process-local (LocMemCache) unless a
shared backend (e.g. Redis) is configured — fine for a single dev server,
but a production deployment running multiple app processes needs a shared
CACHES backend for the lockout to be enforced consistently across them.
"""

from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _cache_key(request):
    return f"pin_login_attempts:{_client_ip(request)}"


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_locked_out(request):
    return cache.get(_cache_key(request), 0) >= MAX_ATTEMPTS


def register_failed_attempt(request):
    key = _cache_key(request)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOCKOUT_SECONDS)


def reset_attempts(request):
    cache.delete(_cache_key(request))
