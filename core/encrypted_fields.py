"""A CharField that transparently Fernet-encrypts its value at rest.

Application code always sees plaintext — ModelForms, Django admin, and
plain attribute access all work unchanged; only the database column holds
ciphertext. Use this for a secret that must be recovered in full later
(e.g. a webhook HMAC key). A value that only ever needs to be *verified*,
never read back, belongs in a one-way hash instead (see accounts.pin for
why that's Argon2id rather than this).
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY)


class EncryptedCharField(models.CharField):
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Pre-encryption legacy row — treat as plaintext; it gets
            # encrypted transparently the next time it's saved.
            return value
