"""PIN hashing and generation for the field login (see accounts.backends.PinBackend).

PINs are looked up by value on every login, so they're hashed with a
deterministic (unsalted) SHA-256 keyed by a server-side pepper rather than
Django's per-user-salted password hasher — that trades a little theoretical
strength for O(1) lookup, and is why login attempts are rate-limited
(accounts.throttling) instead of relying on hashing cost alone.
"""

import hashlib
import secrets

from django.conf import settings

PIN_LENGTH = 6


def hash_pin(raw_pin):
    digest = hashlib.sha256()
    digest.update(settings.PIN_HASH_PEPPER.encode())
    digest.update(raw_pin.encode())
    return digest.hexdigest()


def generate_raw_pin():
    """A cryptographically random PIN_LENGTH-digit numeric string."""
    return "".join(secrets.choice("0123456789") for _ in range(PIN_LENGTH))


def is_valid_pin_format(raw_pin):
    return raw_pin.isdigit() and len(raw_pin) == PIN_LENGTH
