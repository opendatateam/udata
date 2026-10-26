import json
import time
from datetime import datetime

from authlib.common.urls import add_params_to_uri
from authlib.integrations.base_client import OAuthError
from authlib.integrations.flask_client import OAuth
from flask import abort, current_app, redirect, request, session, url_for
from flask_security.tf_plugin import tf_clean_session
from werkzeug.security import gen_salt

from udata.api import API, api
from udata.auth import current_user, login_user
from udata.uris import cdata_url, homepage_url

ns = api.namespace("proconnect", "Proconnect related operations")
oauth = OAuth()
# blueprint = I18nBlueprint("proconnect", __name__, url_prefix="/proconnect")
STATE_KEY = "proconnect_state"
ID_TOKEN_KEY = "id_token"
# When a signed-in agent asked to reauthenticate.
REAUTH_KEY = "proconnect_reauth"
# Leeway between ProConnect's clock and ours when comparing its `auth_time` to ours.
REAUTH_CLOCK_SKEW = 60

AUTH_TIME_CLAIMS = {"id_token": {"auth_time": {"essential": True}}}


def init_app(app):
    if app.config.get("PROCONNECT_OPENID_CONF_URL"):
        # ProConnect SSO
        oauth.init_app(app)
        oauth.register(
            name="proconnect",
            client_id=app.config.get("PROCONNECT_CLIENT_ID"),
            client_secret=app.config.get("PROCONNECT_CLIENT_SECRET"),
            server_metadata_url=app.config.get("PROCONNECT_OPENID_CONF_URL"),
            client_kwargs={"scope": app.config.get("PROCONNECT_SCOPE")},
        )


def get_logout_url():
    id_token = session.get(ID_TOKEN_KEY)
    if id_token is None:
        # No id_token, so no way to logout from ProConnect.
        return None

    metadata = oauth.proconnect.load_server_metadata()
    end_session_endpoint = metadata["end_session_endpoint"]
    # Generate a random state that we send to ProConnect, they'll return it so we can check it.
    state = gen_salt(50)
    session[STATE_KEY] = state
    redirect_uri = url_for("api.proconnect_logout", _external=True)

    return add_params_to_uri(
        end_session_endpoint,
        (
            ("id_token_hint", id_token),
            ("state", state),
            ("post_logout_redirect_uri", redirect_uri),
        ),
    )


def authenticate() -> tuple[dict, dict]:
    """Complete the authorization code flow and return the id_token claims and the user info."""
    token = oauth.proconnect.authorize_access_token()
    # Store the id_token in the session, it'll be used when logging out from ProConnect.
    session[ID_TOKEN_KEY] = token[ID_TOKEN_KEY]
    # /!\ DIRTY HACK.
    # authlib expects the userinfo to either be in the token["id_token"] as a jwt...
    # but in this case, it's not there, it's some other information.
    # We thus need to go get the userinfo from the userinfo_endpoint, but authlib
    # expects it to be plain json. However, proconnect returns a jwt.
    # So we can't use authlib's client.userinfo() helper, we need to do it ourselves.
    metadata = oauth.proconnect.load_server_metadata()
    resp = oauth.proconnect.get(metadata["userinfo_endpoint"])
    resp.raise_for_status()
    # Create a new token that `client.parse_id_token` expects. Replace the initial
    # `id_token` with the jwt we received from the `userinfo_endpoint`.
    userinfo_token = token.copy()
    userinfo_token[ID_TOKEN_KEY] = resp.content
    # authlib has verified the id_token (signature, nonce) in `authorize_access_token`
    # and stored its claims under "userinfo".
    return token["userinfo"], oauth.proconnect.parse_id_token(userinfo_token, nonce=None)


def mark_authenticated_at(auth_time: int) -> None:
    """Date the session's freshness from the moment the agent authenticated at ProConnect.

    `min` because flask-security holds a date up to `SECURITY_FRESHNESS` in the future as
    fresh, a tolerance meant for its own clock and not for ProConnect's.
    """
    session["fs_paa"] = min(auth_time, time.time())
    # A grace period still running holds the session fresh before `fs_paa` is even read,
    # and `login_user` keeps the one a previous user of this browser left behind.
    session.pop("fs_gexp", None)


def verify_page_url(flash: str) -> str:
    return cdata_url("/verify", flash=flash) or homepage_url(flash=flash)


@ns.route("/login/", endpoint="proconnect_login")
class ProconnectLoginAPI(API):
    def get(self):
        if current_app.config["SECURITY_TWO_FACTOR"]:
            # Clean out any potential old session info - in case of previous
            # aborted 2FA attempt.
            tf_clean_session()

        # A reauthentication abandoned before the callback must not apply to this round-trip.
        session.pop(REAUTH_KEY, None)
        params = {"acr_values": "eidas1", "claims": json.dumps(AUTH_TIME_CLAIMS)}
        if request.args.get("reauth"):
            # A browser navigation from the cdata page, whose session may have expired.
            if not current_user.is_authenticated:
                return redirect(verify_page_url("proconnect_reauth_failed"))
            session[REAUTH_KEY] = time.time()
            # Without it, an open ProConnect session answers without asking the agent anything.
            params["max_age"] = 0

        redirect_uri = url_for("api.proconnect_auth", _external=True)
        return oauth.proconnect.authorize_redirect(redirect_uri, **params)


@ns.route("/auth", endpoint="proconnect_auth")
class ProconnectAuthAPI(API):
    def get(self):
        from udata.models import datastore

        reauth_started_at = session.pop(REAUTH_KEY, None)
        if reauth_started_at:
            return reauthenticate(reauth_started_at)

        id_token_claims, proconnect_user = authenticate()
        user = datastore.find_user(email=proconnect_user["email"])
        if not user:
            user = datastore.create_user(
                email=proconnect_user["email"],
                first_name=proconnect_user.get("given_name"),
                last_name=proconnect_user.get("usual_name"),
                confirmed_at=datetime.now(),
            )
        if current_app.config["SECURITY_TWO_FACTOR"]:
            # Enter 2FA check if required
            response = current_app.extensions["security"].two_factor_plugins.tf_enter(
                user=user,
                remember_me=False,
                primary_authn_via="password",
                next_loc=homepage_url(flash="connected"),
            )
            if response:
                return response

        if not login_user(user):
            return {"message": "ProConnect Authentication failed"}, 401
        # `login_user` dated the session now, while an open ProConnect session may have
        # answered for an authentication made long before.
        if auth_time := id_token_claims.get("auth_time"):
            mark_authenticated_at(auth_time)

        return redirect(homepage_url(flash="connected"))


def reauthenticate(started_at: float):
    """Refresh the session of the agent already signed in ("sudo mode"), never sign anyone in.

    Not flask-security's `oauth_verify_*`: it can't pass `max_age=0` to the reauthentication
    alone (the client is shared with the login), and dates the freshness from now rather
    than from `auth_time`, so an open ProConnect session answering would pass for one.
    """
    # The agent may have logged out since: logging out leaves this key in the session.
    if not current_user.is_authenticated:
        return redirect(verify_page_url("proconnect_reauth_failed"))

    try:
        id_token_claims, proconnect_user = authenticate()
    except OAuthError:
        # The agent cancelled, or ProConnect refused the exchange.
        return redirect(verify_page_url("proconnect_reauth_failed"))

    # Compared like the login resolves an account from a ProConnect identity.
    if proconnect_user["email"] != current_user.email:
        return redirect(verify_page_url("proconnect_reauth_identity_mismatch"))

    # An authentication older than the request means ProConnect let its open session
    # answer despite `max_age=0`: it proves nothing about who is at the keyboard now.
    auth_time = id_token_claims.get("auth_time")
    if not auth_time or auth_time < started_at - REAUTH_CLOCK_SKEW:
        return redirect(verify_page_url("proconnect_reauth_failed"))

    mark_authenticated_at(auth_time)
    return redirect(verify_page_url("proconnect_reauth_success"))


@ns.route("/logout_oauth", endpoint="proconnect_logout_oauth")
class ProconnectLogoutOAuthAPI(API):
    def get(self):
        # At the time of this writing, authlib didn't implement OpenIDC session management:
        # https://github.com/lepture/authlib/issues/292
        # So we implement it ourselves. This code may be simplified (or even removed?) in the future
        # if we update to a version that supports it.
        end_session_url = get_logout_url()
        if end_session_url is None:
            return redirect(url_for("security.logout"))

        return redirect(end_session_url)


@ns.route("/logout", endpoint="proconnect_logout")
class ProconnectLogoutAPI(API):
    def get(self):
        # Double check that the request hasn't been forged by checking the random "state" we provided.
        state = request.args["state"]
        stored_state = session.get(STATE_KEY)
        if state != stored_state:
            abort(401)

        # We're logged out from ProConnect, cleanup the ProConnect related data from the session.
        session.pop(ID_TOKEN_KEY, None)
        session.pop(STATE_KEY, None)

        return redirect(url_for("security.logout"))
