import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from flask import current_app

from udata.api import api, fields
from udata.api_fields import field, generate_fields
from udata.models import db

TOKEN_BYTE_LENGTH = 48
PREFIX_DISPLAY_LENGTH = 8
MAX_USER_AGENTS = 20


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
    scope = field(
        db.StringField(choices=["admin"], default="admin"),
        readonly=True,
        description="Token scope",
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
    def generate(cls, user, name=None, expires_at=None):
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
        )
        token.save()
        return token, plaintext

    @classmethod
    def authenticate(cls, plaintext_token):
        """Lookup a token by hashing the plaintext. Returns ApiToken or None."""
        token_hash = _hash_token(plaintext_token)
        token = cls.objects(token_hash=token_hash, revoked_at=None).first()
        if token is None:
            return None
        if token.expires_at and token.expires_at < datetime.now(timezone.utc):
            return None
        return token

    def revoke(self):
        self.revoked_at = datetime.now(timezone.utc)
        self.save()

    def update_usage(self, user_agent=None):
        update_kwargs = {"set__last_used_at": datetime.now(timezone.utc)}
        agents = self.user_agents or []
        if user_agent and user_agent not in agents and len(agents) < MAX_USER_AGENTS:
            update_kwargs["push__user_agents"] = user_agent
        type(self).objects(id=self.id).update_one(**update_kwargs)


apitoken_created_fields = api.inherit(
    "ApiTokenCreated",
    ApiToken.__read_fields__,
    {
        "token": fields.String(
            attribute="_plaintext",
            readonly=True,
            description="The plaintext token (shown only once at creation)",
        ),
    },
)
