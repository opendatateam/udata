import json
import time
from dataclasses import dataclass
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
# The `state` of the ProConnect round-trip reauthenticating a signed-in agent: a login or a
# logout started since has its own, so an abandoned reauthentication can't apply to it.
REAUTH_KEY = "proconnect_reauth"
# The ProConnect levels reached with a second factor: eIDAS substantial and high imply one.
SECOND_FACTOR_ACR_VALUES = ["eidas0-mfa", "eidas1-mfa", "eidas2", "eidas3"]


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


def authorize_redirect(state: str | None = None):
    redirect_uri = url_for("api.proconnect_auth", _external=True)
    if not current_app.config["PROCONNECT_REQUIRE_SECOND_FACTOR"]:
        return oauth.proconnect.authorize_redirect(redirect_uri, acr_values="eidas1", state=state)
    # Required rather than requested: ProConnect then has the agent present a second factor,
    # or set one up, before coming back.
    claims = {"id_token": {"acr": {"essential": True, "values": SECOND_FACTOR_ACR_VALUES}}}
    return oauth.proconnect.authorize_redirect(redirect_uri, state=state, claims=json.dumps(claims))


@dataclass
class ProConnectAuthentication:
    userinfo: dict
    # ProConnect vouches that the agent presented a second factor.
    second_factor: bool


def authenticate() -> ProConnectAuthentication:
    """Complete the authorization code flow and return what ProConnect says of the agent."""
    token = oauth.proconnect.authorize_access_token()
    # authlib leaves the claims of the id_token it verified under `userinfo`.
    acr = token["userinfo"].get("acr")
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
    return ProConnectAuthentication(
        userinfo=oauth.proconnect.parse_id_token(userinfo_token, nonce=None),
        second_factor=acr in SECOND_FACTOR_ACR_VALUES,
    )


def verify_page_url(flash: str) -> str:
    return cdata_url("/verify", flash=flash) or homepage_url(flash=flash)


def login_page_url() -> str:
    """Where a reauthentication goes when the agent isn't signed in anymore."""
    return cdata_url("/login") or homepage_url()


@ns.route("/login/", endpoint="proconnect_login")
class ProconnectLoginAPI(API):
    def get(self):
        if current_app.config["SECURITY_TWO_FACTOR"]:
            # Clean out any potential old session info - in case of previous
            # aborted 2FA attempt.
            tf_clean_session()

        return authorize_redirect()


@ns.route("/reauth/", endpoint="proconnect_reauth")
class ProconnectReauthAPI(API):
    def get(self):
        """Sign the agent out of ProConnect, to sign them back in from `ProconnectLogoutAPI`.

        ProConnect ignores `max_age` and `prompt=login`, and dates `auth_time` from its own
        round-trip: an open ProConnect session would answer without asking the agent anything.
        Signing out closes it, and the session at their identity provider with it when the
        provider lets ProConnect close it.
        """
        # A browser navigation from the cdata page, whose session may have expired.
        if not current_user.is_authenticated:
            return redirect(login_page_url())

        logout_url = get_logout_url()
        # Without the id_token of a ProConnect login, nothing tells ProConnect which session
        # to close.
        if logout_url is None:
            return redirect(verify_page_url("proconnect_reauth_unavailable"))

        session[REAUTH_KEY] = session[STATE_KEY]
        return redirect(logout_url)


@ns.route("/auth", endpoint="proconnect_auth")
class ProconnectAuthAPI(API):
    def get(self):
        from udata.models import datastore

        reauth_state = session.pop(REAUTH_KEY, None)
        if reauth_state and reauth_state == request.args.get("state"):
            return reauthenticate()

        authentication = authenticate()
        proconnect_user = authentication.userinfo
        user = datastore.find_user(email=proconnect_user["email"])
        if not user:
            user = datastore.create_user(
                email=proconnect_user["email"],
                first_name=proconnect_user.get("given_name"),
                last_name=proconnect_user.get("usual_name"),
                confirmed_at=datetime.now(),
            )
        # A second factor presented to ProConnect stands for the udata one, as the identity
        # provider's password stands for the udata one. It may come from a ProConnect session
        # opened earlier, which is why the login stays not fresh below.
        if current_app.config["SECURITY_TWO_FACTOR"] and not authentication.second_factor:
            # Enter 2FA check if required
            response = current_app.extensions["security"].two_factor_plugins.tf_enter(
                user=user,
                remember_me=False,
                primary_authn_via="password",
                next_loc=None,
            )
            if response:
                # flask-security redirects this browser navigation to its own HTML views:
                # send the agent to the cdata pages the password login leads to instead.
                if session.get("tf_state") == "setup_from_login":
                    page = cdata_url("/setup-two-factor")
                else:
                    page = cdata_url("/tf-validate")
                return redirect(page) if page else response

        if not login_user(user):
            return {"message": "ProConnect Authentication failed"}, 401
        # `login_user` dated the session now, while an open ProConnect session may have
        # signed the agent in without asking them anything: only a reauthentication, or
        # the code of the udata 2FA above, makes it fresh. Without `fs_paa`, flask-security
        # ignores the grace period a previous user of this browser may have left.
        session.pop("fs_paa", None)

        return redirect(homepage_url(flash="connected"))


def reauthenticate():
    """Refresh the session of the agent already signed in ("sudo mode"), never sign anyone in."""
    # The agent may have logged out since: logging out leaves this key in the session.
    if not current_user.is_authenticated:
        return redirect(login_page_url())

    try:
        proconnect_user = authenticate().userinfo
    except OAuthError:
        # The agent cancelled, or ProConnect refused the exchange.
        return redirect(verify_page_url("proconnect_reauth_failed"))

    # Compared like the login resolves an account from a ProConnect identity.
    if proconnect_user["email"] != current_user.email:
        return redirect(verify_page_url("proconnect_reauth_identity_mismatch"))

    # Signed out of ProConnect beforehand: their identity provider asked them to authenticate,
    # unless it keeps a session ProConnect can't close.
    session["fs_paa"] = time.time()
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

        session.pop(STATE_KEY, None)
        if session.get(REAUTH_KEY) == state:
            # The id_token signs the agent out again if they cancel and retry, the next
            # authentication replaces it.
            session[REAUTH_KEY] = reauth_state = gen_salt(50)
            return authorize_redirect(state=reauth_state)

        # We're logged out from ProConnect, cleanup the ProConnect related data from the session.
        session.pop(ID_TOKEN_KEY, None)
        return redirect(url_for("security.logout"))
