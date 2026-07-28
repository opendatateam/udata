from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from mongoengine.fields import StringField

# Marks stored values as ciphertext, so to_python can tell them apart from
# fresh plaintext assignments deterministically (mongoengine's Document.__init__
# runs constructor kwargs through to_python too, not just values loaded from
# MongoDB).
CIPHERTEXT_PREFIX = "fernet:"


class EncryptedStringField(StringField):
    """A StringField transparently encrypted at rest with Fernet.

    The key is read lazily from ``current_app.config[key_config]`` on
    encrypt/decrypt rather than at field construction, so this can be
    declared in a Document class body (import time, no app context yet).
    Values are encrypted in ``to_mongo`` (on save) and decrypted in
    ``to_python`` (on load from MongoDB) — like other transform fields
    (e.g. ``udata.mongo.datetime_fields.DateField``), in-memory access
    before a save/reload round-trip sees the plaintext as assigned.

    Stored values carry a ``fernet:`` prefix so decryption only ever runs
    on actual ciphertext, and a decryption failure (wrong or rotated key)
    raises loudly instead of silently passing ciphertext through as the
    value.
    """

    def __init__(self, key_config="GEOPF_TOKEN_ENCRYPTION_KEY", **kwargs):
        self.key_config = key_config
        super().__init__(**kwargs)

    def _fernet(self) -> Fernet:
        key = current_app.config.get(self.key_config)
        if not key:
            raise RuntimeError(f"{self.key_config} is not configured")
        return Fernet(key.encode() if isinstance(key, str) else key)

    def to_mongo(self, value):
        value = super().to_mongo(value)
        if not value:
            return value
        return CIPHERTEXT_PREFIX + self._fernet().encrypt(value.encode()).decode()

    def to_python(self, value):
        value = super().to_python(value)
        if not value or not value.startswith(CIPHERTEXT_PREFIX):
            return value
        ciphertext = value[len(CIPHERTEXT_PREFIX) :]
        try:
            return self._fernet().decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise RuntimeError(
                f"Could not decrypt {self.name!r}: {self.key_config} does not match "
                "the key this value was encrypted with"
            )
