# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId
from datetime import datetime, timedelta

from flask import abort, request
from flask_oauthlib.provider import OAuth2Provider
from werkzeug.security import gen_salt
from werkzeug.exceptions import Unauthorized

from udata import theme
from udata.app import Blueprint, csrf
from udata.auth import current_user, login_required, login_user
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import db
from udata.core.storages import images, default_image_basename


oauth = OAuth2Provider()
bp = Blueprint('oauth', __name__)
i18n = I18nBlueprint('oauth-i18n', __name__)


GRANT_EXPIRATION = 100  # 100 seconds
TOKEN_EXPIRATION = 30 * 24  # 30 days


CLIENT_TYPES = {
    'public': _('Public'),
    'confidential': _('Confidential'),
}

CLIENT_PROFILES = {
    'web': _('Web Application'),
    'user': _('User Agent'),
    'native': _('Native'),
}

GRANT_TYPES = {
    'code': _('Authorization Code'),
    'implicit': _('Implicit'),
    'password': _('Resource Owner Password Credentials'),
    'client': _('Client Credentials'),
}

TOKEN_TYPES = {
    'Bearer': _('Bearer Token'),
}

SCOPES = {
    'default': _('Default scope'),
    'admin': _('System administrator rights')
}


class OAuth2Client(db.Datetimed, db.Document):
    secret = db.StringField(default=lambda: gen_salt(50), required=True)

    type = db.StringField(choices=CLIENT_TYPES.keys(), default='public',
                          required=True)
    profile = db.StringField(choices=CLIENT_PROFILES.keys(), default='web',
                             required=True)
    grant_type = db.StringField(choices=GRANT_TYPES.keys(), default='code',
                                required=True)

    name = db.StringField(required=True)
    description = db.StringField()

    owner = db.ReferenceField('User')
    organization = db.ReferenceField('Organization')
    image = db.ImageField(fs=images, basename=default_image_basename,
                          thumbnails=[150, 25])

    redirect_uris = db.ListField(db.StringField())
    default_scopes = db.ListField(db.StringField(), default=SCOPES.keys())

    meta = {
        'collection': 'oauth2_client'
    }

    @property
    def client_id(self):
        return str(self.id)

    @property
    def client_secret(self):
        return self.secret

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]


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


class OAuth2Token(db.Document):
    client = db.ReferenceField('OAuth2Client', required=True)
    user = db.ReferenceField('User')

    # currently only bearer is supported
    token_type = db.StringField(choices=TOKEN_TYPES.keys(), default='Bearer')

    access_token = db.StringField(unique=True)
    refresh_token = db.StringField(unique=True)
    expires = db.DateTimeField(
        default=lambda: datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION))
    scopes = db.ListField(db.StringField())

    meta = {
        'collection': 'oauth2_token'
    }


@oauth.clientgetter
def load_client(client_id):
    try:
        return OAuth2Client.objects.get(id=ObjectId(client_id))
    except OAuth2Client.DoesNotExist:
        pass


@oauth.grantgetter
def load_grant(client_id, code):
    try:
        return OAuth2Grant.objects.get(client=ObjectId(client_id), code=code)
    except OAuth2Grant.DoesNotExist:
        pass


@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=GRANT_EXPIRATION)
    return OAuth2Grant.objects.create(
        client=ObjectId(client_id),
        code=code['code'],
        redirect_uri=request.redirect_uri,
        scopes=request.scopes,
        user=current_user._get_current_object(),
        expires=expires
    )


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    try:
        if access_token:
            return OAuth2Token.objects.get(access_token=access_token)
        elif refresh_token:
            return OAuth2Token.objects.get(refresh_token=refresh_token)
    except OAuth2Token.DoesNotExist:
        pass


@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    # make sure that every client has only one token connected to a user
    OAuth2Token.objects(client=request.client, user=request.user).delete()

    expires_in = token.pop('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)

    return OAuth2Token.objects.create(
        access_token=token['access_token'],
        refresh_token=token['refresh_token'],
        token_type=token['token_type'],
        scopes=token['scope'].split(),
        expires=expires,
        client=request.client,
        user=request.user,
    )


@bp.route('/oauth/token', methods=['POST'])
@csrf.exempt
@oauth.token_handler
def access_token():
    return None


@i18n.route('/oauth/authorize', methods=['GET', 'POST'])
@oauth.authorize_handler
@login_required
def authorize(*args, **kwargs):
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = OAuth2Client.objects.get(id=ObjectId(client_id))
        kwargs['client'] = client
        return theme.render('api/oauth_authorize.html', oauth=kwargs)
    elif request.method == 'POST':
        accept = 'accept' in request.form
        decline = 'decline' in request.form
        return accept and not decline
    else:
        abort(405)


@i18n.route('/oauth/error')
def oauth_error():
    return theme.render('api/oauth_error.html')


def check_credentials():
    @oauth.require_oauth()
    def log_user_from_oauth_credentials():
        login_user(request.oauth.user)

    try:
        log_user_from_oauth_credentials()
        return True
    except Unauthorized:
        return False


def init_app(app):
    oauth.init_app(app)
    app.register_blueprint(bp)
    app.register_blueprint(i18n)
