"""Rehashes every existing pin_hash from the old unsalted-SHA-256 scheme to
the new deterministic-Argon2id scheme (see accounts.pin.hash_pin).

The old hash can't be reversed to recover the raw PIN, so a user's PIN can
only be carried forward if it was also captured in pin_encrypted (Fernet,
reversible — added just before this migration). Anyone without that has
their PIN cleared instead of silently left on a hash the new login code can
never match again; a manager reissues it from the PIN management screen.

Hashing/decryption logic is inlined rather than imported from
accounts.pin/accounts.models, per this project's standing rule that data
migrations must not depend on live application modules that could be
refactored later and break `manage.py migrate` on a fresh database.
"""

import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import migrations

from argon2.low_level import Type, hash_secret_raw

_ARGON2_TIME_COST = 2
_ARGON2_MEMORY_COST_KIB = 19456
_ARGON2_PARALLELISM = 1
_ARGON2_HASH_LEN = 32


def _hash_pin_argon2id(raw_pin, pepper):
    salt = hashlib.sha256(pepper.encode()).digest()
    digest = hash_secret_raw(
        secret=raw_pin.encode(),
        salt=salt,
        time_cost=_ARGON2_TIME_COST,
        memory_cost=_ARGON2_MEMORY_COST_KIB,
        parallelism=_ARGON2_PARALLELISM,
        hash_len=_ARGON2_HASH_LEN,
        type=Type.ID,
    )
    return digest.hex()


def _decrypt_pin(fernet, encrypted_pin):
    if not encrypted_pin:
        return None
    try:
        return fernet.decrypt(encrypted_pin.encode()).decode()
    except InvalidToken:
        return None


def rehash_pins_with_argon2(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)
    pepper = settings.PIN_HASH_PEPPER

    for user in User.objects.exclude(pin_hash__isnull=True):
        raw_pin = _decrypt_pin(fernet, user.pin_encrypted)
        if raw_pin:
            user.pin_hash = _hash_pin_argon2id(raw_pin, pepper)
            user.save(update_fields=["pin_hash"])
        else:
            user.pin_hash = None
            user.pin_encrypted = None
            user.pin_set_at = None
            user.save(update_fields=["pin_hash", "pin_encrypted", "pin_set_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_user_pin_encrypted"),
    ]

    operations = [
        migrations.RunPython(rehash_pins_with_argon2, migrations.RunPython.noop),
    ]
