"""PIN hashing, encryption and generation for the field login (see
accounts.backends.PinBackend).

PINs are looked up by value on every login, so `hash_pin` is deterministic
(a fixed, pepper-derived salt) rather than per-record salted the way
Django's own password hasher works — that determinism is what makes an
O(1) DB lookup by hash possible. Determinism alone would make the hash as
brute-forceable as a plain SHA-256 digest the moment PIN_HASH_PEPPER leaks
alongside it, so the hash itself is Argon2id (OWASP-recommended memory-hard
parameters): even with the pepper and the full pin_hash column in hand,
testing all 10^6 possible PINs costs real CPU/RAM time per guess instead of
a few milliseconds for the lot. Online guessing is still bounded by
accounts.throttling regardless of hash cost.

Separately, the raw PIN is also kept encrypted (Fernet, FIELD_ENCRYPTION_KEY)
so a manager/SESMT can look it up later from the PIN management screen —
unlike the hash above, this is reversible by design, since that's the whole
point of letting someone view it. Argon2 can't do this: it's a one-way
hash, so it only ever helps *verify* a PIN, never recover one.
"""

import hashlib
import secrets

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

PIN_LENGTH = 6

# OWASP-recommended minimum Argon2id parameters (19 MiB, 2 passes, single
# lane) — deliberately modest so a login request never feels slow under
# concurrent shift-change logins, while still costing real work per guess
# if the hash column ever leaks.
_ARGON2_TIME_COST = 2
_ARGON2_MEMORY_COST_KIB = 19456
_ARGON2_PARALLELISM = 1
_ARGON2_HASH_LEN = 32


def _pin_salt():
    # Fixed, not random: equal PINs must hash identically so the DB can
    # look one up by equality. Secrecy comes from PIN_HASH_PEPPER, not
    # from this salt being unpredictable.
    return hashlib.sha256(settings.PIN_HASH_PEPPER.encode()).digest()


def hash_pin(raw_pin):
    digest = hash_secret_raw(
        secret=raw_pin.encode(),
        salt=_pin_salt(),
        time_cost=_ARGON2_TIME_COST,
        memory_cost=_ARGON2_MEMORY_COST_KIB,
        parallelism=_ARGON2_PARALLELISM,
        hash_len=_ARGON2_HASH_LEN,
        type=Type.ID,
    )
    return digest.hex()


def _fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY)


def encrypt_pin(raw_pin):
    return _fernet().encrypt(raw_pin.encode()).decode()


def decrypt_pin(encrypted_pin):
    """Returns the raw PIN, or None if it can't be decrypted (e.g. it was
    encrypted under a since-rotated FIELD_ENCRYPTION_KEY)."""
    if not encrypted_pin:
        return None
    try:
        return _fernet().decrypt(encrypted_pin.encode()).decode()
    except InvalidToken:
        return None


def generate_raw_pin():
    """A cryptographically random PIN_LENGTH-digit numeric string."""
    return "".join(secrets.choice("0123456789") for _ in range(PIN_LENGTH))


def is_valid_pin_format(raw_pin):
    return raw_pin.isdigit() and len(raw_pin) == PIN_LENGTH
