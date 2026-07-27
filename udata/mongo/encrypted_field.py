from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from mongoengine.fields import StringField


class EncryptedStringField(StringField):
    """A StringField transparently encrypted at rest with Fernet.

    The key is read lazily from ``current_app.config[key_config]`` on
    encrypt/decrypt rather than at field construction, so this can be
    declared in a Document class body (import time, no app context yet).
    Values are encrypted in ``to_mongo`` (on save) and decrypted in
    ``to_python`` (on load from MongoDB) — like other transform fields
    (e.g. ``udata.mongo.datetime_fields.DateField``), in-memory access
    before a save/reload round-trip sees the plaintext as assigned.
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
        return self._fernet().encrypt(value.encode()).decode()

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return value
        # mongoengine's Document.__init__ runs constructor kwargs through
        # to_python too (not just values loaded from MongoDB), so a freshly
        # assigned plaintext value reaches here alongside real ciphertext
        # loaded from the DB. Both are plain strings, indistinguishable by
        # type, so we tell them apart by whether they decrypt.
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            return value
