"""OAuth2 client integration against geopf's Keycloak (sso.geopf.fr, realm geoplateforme).

Mirrors `udata.auth.proconnect`'s client setup, but persists tokens (see `GeopfToken`)
since geopf API calls happen from Celery tasks.
"""

import logging
from datetime import UTC, datetime, timedelta

import requests
from authlib.integrations.flask_client import OAuth
from flask import current_app

from .client import GeopfReauthRequired
from .models import GeopfToken

log = logging.getLogger(__name__)

oauth = OAuth()


def init_app(app):
    if app.config.get("GEOPF_OAUTH_OPENID_CONF_URL"):
        oauth.init_app(app)
        oauth.register(
            name="geopf",
            client_id=app.config.get("GEOPF_OAUTH_CLIENT_ID"),
            client_secret=app.config.get("GEOPF_OAUTH_CLIENT_SECRET"),
            server_metadata_url=app.config.get("GEOPF_OAUTH_OPENID_CONF_URL"),
            client_kwargs={"scope": app.config.get("GEOPF_OAUTH_SCOPE")},
        )


def store_token(user, token: dict) -> GeopfToken:
    """Persist an authlib token dict (from the OAuth callback or a refresh) for `user`."""
    geopf_token = GeopfToken.objects(user=user).first() or GeopfToken(user=user)
    geopf_token.access_token = token["access_token"]
    geopf_token.refresh_token = token["refresh_token"]
    geopf_token.expires_at = datetime.now(UTC) + timedelta(seconds=token["expires_in"])
    geopf_token.save()
    return geopf_token


def _refresh(geopf_token: GeopfToken) -> GeopfToken:
    try:
        token = oauth.geopf.fetch_access_token(
            grant_type="refresh_token", refresh_token=geopf_token.refresh_token
        )
    except Exception as e:
        raise GeopfReauthRequired(
            f"geopf: token refresh failed for user={geopf_token.user.id}: {e}"
        ) from e
    return store_token(geopf_token.user, token)


def revoke_token(geopf_token: GeopfToken) -> None:
    """Best-effort revoke of the refresh token at geopf's oauth server.

    Failures (including no OAuth client configured, an unreachable IdP, or
    a missing revocation_endpoint) are only logged: disconnecting the local
    link must still succeed either way.
    """
    try:
        metadata = oauth.geopf.load_server_metadata()
        revocation_endpoint = metadata["revocation_endpoint"]
        resp = requests.post(
            revocation_endpoint,
            data={
                "token": geopf_token.refresh_token,
                "token_type_hint": "refresh_token",
                "client_id": current_app.config.get("GEOPF_OAUTH_CLIENT_ID"),
                "client_secret": current_app.config.get("GEOPF_OAUTH_CLIENT_SECRET"),
            },
            timeout=10,
        )
        resp.raise_for_status()
    except Exception:
        log.warning(f"geopf: failed to revoke token for user={geopf_token.user.id}", exc_info=True)


def resolve_access_token(user=None, raw_token: str | None = None, min_validity: int = 0) -> str:
    """Return a usable geopf access token for calling the geopf API.

    Pass `raw_token` to bypass storage entirely (ops/debugging, e.g. the CLI's
    `--token` option). Otherwise `user` is required: looks up their stored
    `GeopfToken`, refreshing it first if expired, or if it expires within
    `min_validity` seconds (pass the expected duration of the work ahead so
    the token outlives it).

    Raises `GeopfReauthRequired` when there is no
    token or refresh fails, so the caller (API endpoint, task, CLI) can
    surface a "connect to Géoplateforme" prompt instead of a generic error.
    """
    if raw_token:
        return raw_token
    if user is None:
        raise GeopfReauthRequired("geopf: no user or raw token provided")

    geopf_token = GeopfToken.objects(user=user).first()
    if geopf_token is None:
        raise GeopfReauthRequired(f"geopf: no stored token for user={user.id}")
    if geopf_token.is_expired(within_seconds=min_validity):
        geopf_token = _refresh(geopf_token)
    return geopf_token.access_token
