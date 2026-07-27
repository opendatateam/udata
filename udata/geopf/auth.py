"""OAuth2 client integration against geopf's Keycloak (sso.geopf.fr, realm geoplateforme).

udata is a confidential OIDC client authenticating as the acting data.gouv.fr
user (delegated authorization: "the user's own rights on geopf apply"), not
as a shared service identity. Mirrors `udata.auth.proconnect`'s client setup,
but persists tokens (see `GeopfToken`) since geopf API calls happen from
Celery tasks, long after any browser session that started the link is gone.
"""

from datetime import UTC, datetime, timedelta

from authlib.integrations.flask_client import OAuth

from .client import GeopfReauthRequired
from .models import GeopfToken

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


def resolve_access_token(user=None, raw_token: str | None = None) -> str:
    """Return a usable geopf access token for calling the geopf API.

    Pass `raw_token` to bypass storage entirely (ops/debugging, e.g. the CLI's
    `--token` option). Otherwise `user` is required: looks up their stored
    `GeopfToken`, refreshing it first if expired. Raises `GeopfReauthRequired`
    when there is no token or refresh fails, so the caller (API endpoint, task,
    CLI) can surface a "connect to Géoplateforme" prompt instead of a generic
    error.
    """
    if raw_token:
        return raw_token
    if user is None:
        raise GeopfReauthRequired("geopf: no user or raw token provided")

    geopf_token = GeopfToken.objects(user=user).first()
    if geopf_token is None:
        raise GeopfReauthRequired(f"geopf: no stored token for user={user.id}")
    if geopf_token.is_expired():
        geopf_token = _refresh(geopf_token)
    return geopf_token.access_token
