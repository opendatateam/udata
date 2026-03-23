import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from flask import current_app

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.models import db

TOKEN_BYTE_LENGTH = 48
PREFIX_DISPLAY_LENGTH = 8
MAX_USER_AGENTS = 20


def parse_future_datetime(value):
    """Parse an ISO 8601 string into a tz-aware datetime that must be in the future.
    Aborts with 400 on invalid format or past date."""
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        api.abort(400, "Invalid expires_at format")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if dt < datetime.now(timezone.utc):
        api.abort(400, "expires_at must be in the future")
    return dt


def _hash_token(plaintext):
    key = current_app.config["API_TOKEN_SECRET"].encode()
    return hmac.new(key, plaintext.encode(), hashlib.sha256).hexdigest()


@generate_fields()
class ApiToken(db.Document):
    token_hash = db.StringField(required=True, unique=True)
    token_prefix = field(
        db.StringField(required=True),
        readonly=True,
        description="First characters of the token for identification",
    )
    user = db.ReferenceField("User", required=True, reverse_delete_rule=db.CASCADE)
    name = field(
        db.StringField(max_length=255),
        description="User-given label for this token",
    )
    scopes = field(
        db.ListField(db.StringField(choices=["admin"]), default=lambda: ["admin"]),
        description="Token scopes",
    )
    kind = field(
        db.StringField(choices=["api_key"], default="api_key"),
        readonly=True,
        description="Token type",
    )
    created_at = field(
        db.DateTimeField(default=lambda: datetime.now(timezone.utc), required=True),
        readonly=True,
        description="Token creation date",
    )
    last_used_at = field(
        db.DateTimeField(),
        readonly=True,
        description="Last time this token was used",
    )
    user_agents = field(
        db.ListField(db.StringField()),
        readonly=True,
        description="User agents that have used this token",
    )
    revoked_at = field(
        db.DateTimeField(),
        readonly=True,
        description="When this token was revoked",
    )
    expires_at = field(
        db.DateTimeField(),
        description="When this token expires",
    )

    meta = {
        "collection": "api_token",
        "indexes": [
            "token_hash",
            "user",
            ("user", "-created_at"),
        ],
        "ordering": ["-created_at"],
    }

    @classmethod
    def generate(cls, user, name=None, expires_at=None, scopes=None):
        """Create a new token. Returns (ApiToken, plaintext_token)."""
        prefix = current_app.config.get("API_TOKEN_PREFIX", "udata_")
        raw = secrets.token_urlsafe(TOKEN_BYTE_LENGTH)
        plaintext = f"{prefix}{raw}"
        token_hash = _hash_token(plaintext)
        display_prefix = plaintext[: len(prefix) + PREFIX_DISPLAY_LENGTH]
        token = cls(
            token_hash=token_hash,
            token_prefix=display_prefix,
            user=user,
            name=name,
            expires_at=expires_at,
            scopes=scopes or ["admin"],
        )
        token.save()
        return token, plaintext

    @classmethod
    def authenticate(cls, plaintext_token):
        """Lookup a token by hashing the plaintext.

        Returns (ApiToken, None) on success, or (None, error_reason) on failure.
        error_reason is one of: "invalid", "revoked", "expired".
        """
        token_hash = _hash_token(plaintext_token)
        token = cls.objects(token_hash=token_hash).first()
        if token is None:
            return None, "invalid"
        if token.revoked_at is not None:
            return None, "revoked"
        if token.expires_at:
            expires_at = token.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return None, "expired"
        return token, None

    def revoke(self):
        self.revoked_at = datetime.now(timezone.utc)
        self.save()

    def update_usage(self, user_agent=None):
        update_kwargs = {"set__last_used_at": datetime.now(timezone.utc)}
        agents = self.user_agents or []
        if user_agent and len(agents) < MAX_USER_AGENTS:
            update_kwargs["add_to_set__user_agents"] = user_agent
        type(self).objects(id=self.id).update_one(**update_kwargs)
