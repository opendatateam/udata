from datetime import UTC, datetime, timedelta

from udata.models import db
from udata.mongo.encrypted_field import EncryptedStringField


class GeopfToken(db.Document):
    """Per-user OAuth2 tokens used to call the Géoplateforme entrepôt API on their behalf.

    One token per data.gouv.fr user, obtained via the authorization_code flow
    against geopf's Keycloak (see udata/geopf/api.py) and refreshed as needed
    before each call (see udata/geopf/auth.py).
    """

    user = db.ReferenceField("User", required=True, unique=True, reverse_delete_rule=db.CASCADE)
    access_token = EncryptedStringField(required=True)
    refresh_token = EncryptedStringField(required=True)
    expires_at = db.DateTimeField(required=True)
    created_at = db.DateTimeField(default=lambda: datetime.now(UTC), required=True)

    meta = {"collection": "geopf_token"}

    def is_expired(self, within_seconds: int = 0) -> bool:
        """Whether the token is expired, or will be within `within_seconds`."""
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC) + timedelta(seconds=within_seconds)
