"""
OAuth 2 serveur implementation based on Authlib.

See the documentatiosn here:
 - https://docs.authlib.org/en/latest/flask/oauth2.html
 - https://docs.authlib.org/en/latest/spec/rfc6749.html
 - https://docs.authlib.org/en/latest/spec/rfc6750.html
 - https://docs.authlib.org/en/latest/spec/rfc7009.html

Authlib provides SQLAlchemny mixins which help understanding:
 - https://github.com/lepture/authlib/blob/master/authlib/flask/oauth2/sqla.py

As well as a sample application:
 - https://github.com/authlib/example-oauth2-server
"""

import fnmatch
import time
from datetime import datetime, timedelta

from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.integrations.flask_oauth2.errors import (
    _HTTPException as AuthlibFlaskException,
)
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import ClientMixin, grants
from authlib.oauth2.rfc6749.util import list_to_scope, scope_to_list
from authlib.oauth2.rfc6750 import BearerTokenValidator
from authlib.oauth2.rfc7009 import RevocationEndpoint
from authlib.oauth2.rfc7636 import CodeChallenge
from bson import ObjectId
from flask import current_app, render_template, request
from flask_security.utils import verify_password
from werkzeug.exceptions import Unauthorized

from udata.app import csrf
from udata.auth import current_user, login_required, login_user
from udata.core.organization.models import Organization
from udata.core.storages import default_image_basename, images
from udata.i18n import I18nBlueprint
from udata.i18n import lazy_gettext as _
from udata.mongo import db

blueprint = I18nBlueprint("oauth", __name__, url_prefix="/oauth")
oauth = AuthorizationServer()
require_oauth = ResourceProtector()


GRANT_EXPIRATION = 100  # 100 seconds
TOKEN_EXPIRATION = 30 * 24 * 60 * 60  # 30 days in seconds
REFRESH_EXPIRATION = 30  # days
EPOCH = datetime.fromtimestamp(0)

TOKEN_TYPES = {
    "Bearer": _("Bearer Token"),
}

SCOPES = {"default": _("Default scope"), "admin": _("System administrator rights")}


class OAuth2Client(ClientMixin, db.Datetimed, db.Document):
    secret = db.StringField(default=None)

    name = db.StringField(required=True)
    description = db.StringField()

    owner = db.ReferenceField("User")
    organization = db.ReferenceField(Organization, reverse_delete_rule=db.NULLIFY)
    image = db.ImageField(fs=images, basename=default_image_basename, thumbnails=[150, 25])

    redirect_uris = db.ListField(db.StringField())
    scope = db.StringField(default="default")
    grant_types = db.ListField(db.StringField())
    response_types = db.ListField(db.StringField())

    confidential = db.BooleanField(default=False)
    internal = db.BooleanField(default=False)

    meta = {"collection": "oauth2_client"}

    def get_client_id(self):
        return str(self.id)

    @property
    def client_id(self):
        return self.get_client_id()

    @property
    def client_secret(self):
        return self.secret

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    def get_default_redirect_uri(self):
        return self.default_redirect_uri

    def get_allowed_scope(self, scope):
        if not scope:
            return ""
        allowed = set(scope_to_list(self.scope))
        return list_to_scope([s for s in scope.split() if s in allowed])

    def check_redirect_uri(self, redirect_uri):
        if current_app.config.get("OAUTH2_ALLOW_WILDCARD_IN_REDIRECT_URI"):
            return any(fnmatch.fnmatch(redirect_uri, pattern) for pattern in self.redirect_uris)
        else:
            return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret):
        return self.secret == client_secret

    def check_endpoint_auth_method(self, method, _endpoint):
        if not self.has_client_secret():
            return method == "none"
        return method in ("client_secret_post", "client_secret_basic")

    def check_response_type(self, response_type):
        return True

    def check_grant_type(self, grant_type):
        return True

    def check_requested_scope(self, scope):
        allowed = set(self.scope)
        return allowed.issuperset(set(scope))

    def has_client_secret(self):
        return bool(self.secret)


class OAuth2Token(db.Document):
    client = db.ReferenceField("OAuth2Client", required=True)
    user = db.ReferenceField("User")

    # currently only bearer is supported
    token_type = db.StringField(choices=list(TOKEN_TYPES), default="Bearer")

    access_token = db.StringField(unique=True)
    refresh_token = db.StringField(unique=True, sparse=True)
    created_at = db.DateTimeField(default=datetime.utcnow, required=True)
    expires_in = db.IntField(required=True, default=TOKEN_EXPIRATION)
    scope = db.StringField(default="")
    revoked = db.BooleanField(default=False)

    meta = {"collection": "oauth2_token"}

    def __str__(self):
        return "<OAuth2Token({0.client.name})>".format(self)

    def check_client(self, client):
        return self.client == client

    def get_scope(self):
        return self.scope

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return (self.created_at - EPOCH).total_seconds() + self.expires_in

    def get_client_id(self):
        return str(self.client.id)

    def is_expired(self):
        now = time.time()
        return self.get_expires_at() < now

    def is_revoked(self):
        return self.revoked

    def is_refresh_token_valid(self):
        if self.revoked:
            return False
        expired_at = datetime.fromtimestamp(self.get_expires_at())
        expired_at += timedelta(days=REFRESH_EXPIRATION)
        return expired_at > datetime.utcnow()


class OAuth2Code(db.Document):
    user = db.ReferenceField("User", required=True)
    client = db.ReferenceField("OAuth2Client", required=True)

    code = db.StringField(required=True)

    redirect_uri = db.StringField()
    expires = db.DateTimeField()

    scope = db.StringField(default="")
    code_challenge = db.StringField()
    code_challenge_method = db.StringField()

    meta = {"collection": "oauth2_code"}

    def __str__(self):
        return "<OAuth2Code({0.client.name}, {0.user.fullname})>".format(self)

    def is_expired(self):
        return self.expires < datetime.utcnow()

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return self.scope


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["none", "client_secret_basic", "client_secret_post"]

    def save_authorization_code(self, code, request):
        code_challenge = request.data.get("code_challenge")
        code_challenge_method = request.data.get("code_challenge_method")
        expires = datetime.utcnow() + timedelta(seconds=GRANT_EXPIRATION)
        auth_code = OAuth2Code.objects.create(
            code=code,
            client=ObjectId(request.client.client_id),
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user=ObjectId(request.user.id),
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires=expires,
        )
        return auth_code

    def query_authorization_code(self, code, client):
        auth_code = OAuth2Code.objects(code=code, client=client).first()
        if auth_code and not auth_code.is_expired():
            return auth_code

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        return authorization_code.user


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        from udata.core.user.models import User

        user = User.objects(email=username).first()
        if user and verify_password(password, user.password):
            return user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        item = OAuth2Token.objects(refresh_token=refresh_token).first()
        if item and item.is_refresh_token_valid():
            return item

    def authenticate_user(self, credential):
        return credential.user

    def revoke_old_credential(self, credential):
        credential.revoked = True
        credential.save()


class RevokeToken(RevocationEndpoint):
    CLIENT_AUTH_METHODS = ["none", "client_secret_basic"]

    def query_token(self, token_string, token_type_hint):
        qs = OAuth2Token.objects()
        if token_type_hint == "access_token":
            return qs.filter(access_token=token_string).first()
        elif token_type_hint == "refresh_token":
            return qs.filter(refresh_token=token_string).first()
        else:
            qs = qs(db.Q(access_token=token_string) | db.Q(refresh_token=token_string))
            return qs.first()

    def revoke_token(self, token, _request):
        token.revoked = True
        token.save()


class BearerToken(BearerTokenValidator):
    def authenticate_token(self, token_string):
        return OAuth2Token.objects(access_token=token_string).first()

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return token.revoked


@blueprint.route("/token", methods=["POST"], localize=False, endpoint="token")
@csrf.exempt
def access_token():
    return oauth.create_token_response()


@blueprint.route("/revoke", methods=["POST"], localize=False)
@csrf.exempt
def revoke_token():
    return oauth.create_endpoint_response(RevokeToken.ENDPOINT_NAME)


@blueprint.route("/authorize", methods=["GET", "POST"])
@login_required
def authorize(*args, **kwargs):
    if request.method == "GET":
        try:
            grant = oauth.get_consent_grant(end_user=current_user)
        except OAuth2Error as error:
            return error.error
        # Bypass authorization screen for internal clients
        if grant.client.internal:
            return oauth.create_authorization_response(grant_user=current_user)
        return render_template("api/oauth_authorize.html", grant=grant)
    elif request.method == "POST":
        accept = "accept" in request.form
        decline = "decline" in request.form
        if accept and not decline:
            grant_user = current_user
        else:
            grant_user = None
        return oauth.create_authorization_response(grant_user=grant_user)


@blueprint.route("/error")
def oauth_error():
    return render_template("api/oauth_error.html")


def query_client(client_id):
    """Fetch client by ID"""
    return OAuth2Client.objects(id=ObjectId(client_id)).first()


def save_token(token, request):
    scope = token.pop("scope", "")
    client = request.client
    user = request.user or client.owner
    if request.grant_type == "refresh_token":
        old_token = OAuth2Token.objects(
            refresh_token=request.refresh_token.refresh_token, client=client, user=user, scope=scope
        ).first()
        old_token.update(**token)
    else:
        OAuth2Token.objects.create(client=client, user=user, scope=scope, **token)


def check_credentials():
    try:
        with require_oauth.acquire() as token:
            login_user(token.user)
        return True
    except (Unauthorized, AuthlibFlaskException):
        return False


def init_app(app):
    oauth.init_app(app, query_client=query_client, save_token=save_token)

    # support all grants
    oauth.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=True)])
    oauth.register_grant(PasswordGrant)
    oauth.register_grant(RefreshTokenGrant)
    oauth.register_grant(grants.ClientCredentialsGrant)

    # support revocation endpoint
    oauth.register_endpoint(RevokeToken)

    require_oauth.register_token_validator(BearerToken())
    app.register_blueprint(blueprint)
