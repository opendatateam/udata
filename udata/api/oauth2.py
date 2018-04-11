# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
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
'''

from bson import ObjectId

from datetime import datetime, timedelta

from authlib.common.security import generate_token
from authlib.flask.oauth2 import (
    AuthorizationServer, ResourceProtector, current_token
)
from authlib.specs.rfc6749 import grants, ClientMixin
from authlib.specs.rfc6750 import BearerTokenValidator
from authlib.specs.rfc7009 import RevocationEndpoint
from flask import abort, request
from flask_security.utils import verify_password
from werkzeug.exceptions import Unauthorized
from werkzeug.security import gen_salt

from udata import theme
from udata.app import csrf
from udata.auth import current_user, login_required, login_user
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import db
from udata.core.user.models import User
from udata.core.storages import images, default_image_basename


blueprint = I18nBlueprint('oauth', __name__, url_prefix='/oauth')
oauth = AuthorizationServer()
require_oauth = ResourceProtector()


GRANT_EXPIRATION = 100  # 100 seconds
TOKEN_EXPIRATION = 30 * 24 * 60 * 60  # 30 days in seconds
REFRESH_EXPIRATION = 30  # days
EPOCH = datetime.fromtimestamp(0)

TOKEN_TYPES = {
    'Bearer': _('Bearer Token'),
}

SCOPES = {
    'default': _('Default scope'),
    'admin': _('System administrator rights')
}


class OAuth2Client(ClientMixin, db.Datetimed, db.Document):
    secret = db.StringField(default=lambda: gen_salt(50))

    name = db.StringField(required=True)
    description = db.StringField()

    owner = db.ReferenceField('User')
    organization = db.ReferenceField('Organization')
    image = db.ImageField(fs=images, basename=default_image_basename,
                          thumbnails=[150, 25])

    redirect_uris = db.ListField(db.StringField())
    scopes = db.ListField(db.StringField(), default=['default'])

    confidential = db.BooleanField(default=False)
    internal = db.BooleanField(default=False)

    meta = {
        'collection': 'oauth2_client'
    }

    def __unicode__(self):
        return self.name

    @property
    def client_id(self):
        return str(self.id)

    @property
    def client_secret(self):
        return self.secret

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    def get_default_redirect_uri(self):
        '''Implement required ClientMixin method'''
        return self.default_redirect_uri

    def check_redirect_uri(self, redirect_uri):
        '''Implement required ClientMixin method'''
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret):
        return self.secret == client_secret

    def check_token_endpoint_auth_method(self, method):
        if not self.has_client_secret():
            return method == 'none'
        return method in ('client_secret_post', 'client_secret_basic')

    def check_response_type(self, response_type):
        return True

    def check_grant_type(self, grant_type):
        return True

    def check_requested_scopes(self, scopes):
        allowed = set(self.scopes)
        return allowed.issuperset(set(scopes))

    def has_client_secret(self):
        return bool(self.secret)


class OAuth2Grant(db.Document):
    user = db.ReferenceField('User', required=True)
    client = db.ReferenceField('OAuth2Client', required=True)

    code = db.StringField(required=True)

    redirect_uri = db.StringField()
    expires = db.DateTimeField()

    scopes = db.ListField(db.StringField())

    meta = {
        'collection': 'oauth2_grant'
    }

    def __unicode__(self):
        return '<OAuth2Grant({0.client.name}, {0.user.fullname})>'.format(self)

    def is_expired(self):
        return self.expires < datetime.utcnow()

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return ' '.join(self.scopes)


class OAuth2Token(db.Document):
    client = db.ReferenceField('OAuth2Client', required=True)
    user = db.ReferenceField('User')

    # currently only bearer is supported
    token_type = db.StringField(choices=TOKEN_TYPES.keys(), default='Bearer')

    access_token = db.StringField(unique=True)
    refresh_token = db.StringField(unique=True, sparse=True)
    created_at = db.DateTimeField(default=datetime.utcnow, required=True)
    expires_in = db.IntField(required=True, default=TOKEN_EXPIRATION)
    scopes = db.ListField(db.StringField())

    meta = {
        'collection': 'oauth2_token'
    }

    def __unicode__(self):
        return '<OAuth2Token({0.client.name})>'.format(self)

    def get_scope(self):
        return ' '.join(self.scopes)

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return (self.created_at - EPOCH).total_seconds() + self.expires_in

    def is_refresh_token_expired(self):
        expired_at = datetime.fromtimestamp(self.get_expires_at())
        expired_at += timedelta(days=REFRESH_EXPIRATION)
        return expired_at < datetime.utcnow()


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        'client_secret_basic',
        'client_secret_post',
    ]

    def create_authorization_code(self, client, grant_user, request):
        code = generate_token(48)
        expires = datetime.utcnow() + timedelta(seconds=GRANT_EXPIRATION)
        scopes = request.scope.split(' ') if request.scope else client.scopes
        OAuth2Grant.objects.create(
            code=code,
            client=client,
            redirect_uri=request.redirect_uri,
            scopes=scopes,
            user=ObjectId(grant_user.id),
            expires=expires,
        )
        return code

    def parse_authorization_code(self, code, client):
        item = OAuth2Grant.objects(code=code, client=client).first()
        if item and not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        return authorization_code.user


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        user = User.objects(email=username).first()
        if user and verify_password(password, user.password):
            return user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        token = OAuth2Token.objects(refresh_token=refresh_token).first()
        if token and not token.is_refresh_token_expired():
            return token

    def authenticate_user(self, credential):
        return credential.user


class RevokeToken(RevocationEndpoint):
    def query_token(self, token, token_type_hint, client):
        qs = OAuth2Token.objects(client=client)
        if token_type_hint:
            qs = qs(**{token_type_hint: token})
        else:
            qs = qs(db.Q(access_token=token) | db.Q(refresh_token=token))
        return qs.first()

    def revoke_token(self, token):
        # TODO: mark token as revoked
        token.delete()


class BearerToken(BearerTokenValidator):
    def authenticate_token(self, token_string):
        return OAuth2Token.objects(access_token=token_string).first()

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        # TODO: return token.revoked
        return False


@blueprint.route('/token', methods=['POST'], localize=False, endpoint='token')
@csrf.exempt
def access_token():
    return oauth.create_token_response()


@blueprint.route('/revoke', methods=['POST'], localize=False)
def revoke_token():
    return oauth.create_endpoint_response(RevokeToken.ENDPOINT_NAME)


@blueprint.route('/authorize', methods=['GET', 'POST'])
@login_required
def authorize(*args, **kwargs):
    if request.method == 'GET':
        grant = oauth.validate_consent_request(end_user=current_user)
        # Bypass authorization screen for internal clients
        if grant.client.internal:
            return oauth.create_authorization_response(grant_user=current_user)
        return theme.render('api/oauth_authorize.html', grant=grant)
    elif request.method == 'POST':
        accept = 'accept' in request.form
        decline = 'decline' in request.form
        if accept and not decline:
            grant_user = current_user
        else:
            grant_user = None
        return oauth.create_authorization_response(grant_user=grant_user)
    else:
        abort(405)


@blueprint.route('/error')
def oauth_error():
    return theme.render('api/oauth_error.html')


def query_client(client_id):
    '''Fetch client by ID'''
    return OAuth2Client.objects(id=ObjectId(client_id)).first()


def save_token(token, request):
    scopes = token.pop('scope', '').split(' ')
    if request.grant_type == 'refresh_token':
        credential = request.credential
        credential.update(scopes=scopes, **token)
    else:
        client = request.client
        user = request.user or client.owner
        OAuth2Token.objects.create(
            client=client,
            user=user.id,
            scopes=scopes,
            **token
        )


def check_credentials():
    @require_oauth(None)
    def log_user_from_oauth_credentials():
        login_user(current_token.user)

    try:
        log_user_from_oauth_credentials()
        return True
    except Unauthorized:
        return False


def init_app(app):
    oauth.init_app(app, query_client=query_client, save_token=save_token)

    # support all grants
    oauth.register_grant(AuthorizationCodeGrant)
    oauth.register_grant(PasswordGrant)
    oauth.register_grant(RefreshTokenGrant)
    oauth.register_grant(grants.ClientCredentialsGrant)
    oauth.register_grant(grants.ImplicitGrant)

    # support revocation endpoint
    oauth.register_endpoint(RevokeToken)

    require_oauth.register_token_validator(BearerToken())
    app.register_blueprint(blueprint)
