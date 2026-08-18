from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY)


class EncryptedCharField(models.CharField):
    """A CharField encrypted at rest with a dedicated key (settings.FIELD_ENCRYPTION_KEY,
    separate from SECRET_KEY) — for values the app needs to read back as-is, unlike a
    password (which is hashed instead, since it never needs to be recovered). A raw
    database dump/backup leak alone isn't enough to read these; the key is needed too.

    Ciphertext is meaningfully longer than the plaintext (Fernet adds a version byte,
    timestamp, IV, and HMAC, then base64-encodes it all), so max_length must be sized
    generously — the field won't silently truncate, but saves will fail loudly if
    max_length is too tight for the encrypted output.
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return _get_fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Not a value this key can decrypt — a key rotation without re-encrypting
            # old rows, or (pre-migration) genuinely still plaintext. Surface as empty
            # rather than raising on every request that touches this field/row.
            return ''
