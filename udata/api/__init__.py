# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import urllib

from functools import wraps

from flask import (
    current_app, g, request, url_for, json, make_response, redirect, Blueprint
)
from flask_fs import UnauthorizedFileType
from flask_restplus import Api, Resource, cors

from udata import search, theme, tracking
from udata.app import csrf
from udata.i18n import I18nBlueprint, get_locale
from udata.auth import (
    current_user, login_user, Permission, RoleNeed, PermissionDenied
)
from udata.core.user.models import User
from udata.core.organization.models import Organization
from udata.sitemap import sitemap
from udata.utils import safe_unicode

from . import fields, oauth2
from .signals import on_api_call


log = logging.getLogger(__name__)

apiv1 = Blueprint('api', __name__, url_prefix='/api/1')
apidoc = I18nBlueprint('apidoc', __name__)


DEFAULT_PAGE_SIZE = 50
HEADER_API_KEY = 'X-API-KEY'

# TODO: make upstream flask-restplus automatically handle
# flask-restplus headers and allow lazy evaluation
# of headers (ie. callable)
PREFLIGHT_HEADERS = (
    HEADER_API_KEY,
    'X-Fields',
    'Content-Type',
    'Accept',
    'Accept-Charset',
    'Accept-Language',
    'Cache-Control',
    'Content-Encoding',
    'Content-Length',
    'Content-Security-Policy',
    'Content-Type',
    'Cookie',
    'ETag',
    'Host',
    'If-Modified-Since',
    'Keep-Alive',
    'Last-Modified',
    'Origin',
    'Referer',
    'User-Agent',
    'X-Forwarded-For',
    'X-Forwarded-Port',
    'X-Forwarded-Proto',
)


class UDataApi(Api):
    def __init__(self, app=None, **kwargs):
        decorators = kwargs.pop('decorators', []) or []
        kwargs['decorators'] = [self.authentify] + decorators
        super(UDataApi, self).__init__(app, **kwargs)
        self.authorizations = {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': HEADER_API_KEY
            }
        }

    def secure(self, func):
        '''Enforce authentication on a given method/verb
        and optionnaly check a given permission
        '''
        if isinstance(func, basestring):
            return self._apply_permission(Permission(RoleNeed(func)))
        elif isinstance(func, Permission):
            return self._apply_permission(func)
        else:
            return self._apply_secure(func)

    def _apply_permission(self, permission):
        def wrapper(func):
            return self._apply_secure(func, permission)
        return wrapper

    def _apply_secure(self, func, permission=None):
        '''Enforce authentication on a given method/verb'''
        self._handle_api_doc(func, {'security': 'apikey'})

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                self.abort(401)

            if permission is not None:
                with permission.require():
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    def authentify(self, func):
        '''Authentify the user if credentials are given'''
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                return func(*args, **kwargs)

            apikey = request.headers.get(HEADER_API_KEY)
            if apikey:
                try:
                    user = User.objects.get(apikey=apikey)
                except User.DoesNotExist:
                    self.abort(401, 'Invalid API Key')

                if not login_user(user, False):
                    self.abort(401, 'Inactive user')
            else:
                oauth2.check_credentials()
            return func(*args, **kwargs)
        return wrapper

    def validate(self, form_cls, obj=None):
        '''Validate a form from the request and handle errors'''
        if 'application/json' not in request.headers.get('Content-Type'):
            errors = {'Content-Type': 'expecting application/json'}
            self.abort(400, errors=errors)
        form = form_cls.from_json(request.json, obj=obj, instance=obj,
                                  csrf_enabled=False)
        if not form.validate():
            self.abort(400, errors=form.errors)
        return form

    def render_ui(self):
        return redirect(url_for('apii18n.apidoc'))

    def unauthorized(self, response):
        '''Override to change the WWW-Authenticate challenge'''
        realm = current_app.config.get('HTTP_OAUTH_REALM', 'uData')
        challenge = 'Bearer realm="{0}"'.format(realm)

        response.headers['WWW-Authenticate'] = challenge
        return response

    def page_parser(self):
        parser = self.parser()
        parser.add_argument('page', type=int, default=1, location='args',
                            help='The page to fetch')
        parser.add_argument('page_size', type=int, default=20, location='args',
                            help='The page size to fetch')
        return parser


api = UDataApi(
    apiv1,
    decorators=[csrf.exempt,
                cors.crossdomain(origin='*',
                                 credentials=True,
                                 headers=PREFLIGHT_HEADERS
                )
    ],
    version='1.0', title='uData API',
    description='uData API', default='site',
    default_label='Site global namespace'
)


api.model_reference = api.model('ModelReference', {
    'class': fields.ClassName(description='The model class', required=True),
    'id': fields.String(description='The object identifier', required=True),
})


@api.representation('application/json')
def output_json(data, code, headers=None):
    '''Use Flask JSON to serialize'''
    resp = make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


@apiv1.before_request
def set_api_language():
    if 'lang' in request.args:
        g.lang_code = request.args['lang']
    else:
        g.lang_code = get_locale()


def extract_name_from_path(path):
    """Return a readable name from a URL path.

    Useful to log requests on Piwik with categories tree structure.
    See: http://piwik.org/faq/how-to/#faq_62
    """
    base_path, query_string = path.split('?')
    infos = base_path.strip('/').split('/')[2:]  # Removes api/version.
    if len(infos) > 1:  # This is an object.
        name = '{category} / {name}'.format(
            category=infos[0].title(),
            name=infos[1].replace('-', ' ').title()
        )
    else:  # This is a collection.
        name = '{category}'.format(category=infos[0].title())
    return safe_unicode(name)


@apiv1.after_request
def collect_stats(response):
    action_name = extract_name_from_path(request.full_path)
    blacklist = current_app.config.get('TRACKING_BLACKLIST', [])
    if (not current_app.config['TESTING'] and
            request.endpoint not in blacklist):
        extras = {
            'action_name': urllib.quote(action_name),
        }
        tracking.send_signal(on_api_call, request, current_user, **extras)
    return response


default_error = api.model('Error', {
    'message': fields.String
})


@api.errorhandler(PermissionDenied)
@api.marshal_with(default_error, code=403)
def handle_permission_denied(error):
    '''Error occuring when the user does not have the required permissions'''
    message = 'You do not have the permission to modify that object.'
    return {'message': message}, 403


@api.errorhandler(ValueError)
@api.marshal_with(default_error, code=400)
def handle_value_error(error):
    '''A generic value error'''
    return {'message': str(error)}, 400


@api.errorhandler(UnauthorizedFileType)
@api.marshal_with(default_error, code=400)
def handle_unauthorized_file_type(error):
    '''Error occuring when the user try to upload a non-allowed file type'''
    url = url_for('api.allowed_extensions', _external=True)
    msg = (
        'This file type is not allowed.'
        'The allowed file type list is available at {url}'
    ).format(url=url)
    return {'message': msg}, 400


@apidoc.route('/api/')
@apidoc.route('/api/1/')
@api.documentation
def default_api():
    return redirect(url_for('apidoc.swaggerui'))


@apidoc.route('/apidoc/')
def swaggerui():
    params = {"datasets": "many"}
    organizations = search.iter(Organization, **params)
    return theme.render('apidoc.html', specs_url=api.specs_url, organizations=organizations)


@sitemap.register_generator
def api_sitemap_urls():
    yield 'apidoc.swaggerui_redirect', {}, None, 'weekly', 0.9


@apidoc.route('/apidoc/images/<path:path>')
def images(path):
    return redirect(url_for('static',
                    filename='bower/swagger-ui/dist/images/' + path))


@apidoc.route('/static/images/throbber.gif')
def fix_apidoc_throbber():
    return redirect(url_for('static',
                    filename='bower/swagger-ui/dist/images/throbber.gif'))


class API(Resource):  # Avoid name collision as resource is a core model
    @api.hide
    def options(self):
        pass  # Only here to allow default Flask response


base_reference = api.model('BaseReference', {
    'id': fields.String(description='The object unique identifier',
                        required=True),
    'class': fields.ClassName(description='The object class',
                              discriminator=True, required=True),
}, description='Base model for reference field, aka. inline model reference')


def marshal_page(page, page_fields):
    return api.marshal(page, fields.pager(page_fields))


def marshal_page_with(func):
    pass


def init_app(app):
    # Load all core APIs
    import udata.core.activity.api  # noqa
    import udata.core.spatial.api  # noqa
    import udata.core.metrics.api  # noqa
    import udata.core.user.api  # noqa
    import udata.core.dataset.api  # noqa
    import udata.core.issues.api  # noqa
    import udata.core.discussions.api  # noqa
    import udata.core.reuse.api  # noqa
    import udata.core.organization.api  # noqa
    import udata.core.followers.api  # noqa
    import udata.core.jobs.api  # noqa
    import udata.core.site.api  # noqa
    import udata.core.tags.api  # noqa
    import udata.core.topic.api  # noqa
    import udata.core.post.api  # noqa
    import udata.features.transfer.api  # noqa
    import udata.features.notifications.api  # noqa
    import udata.features.oembed.api  # noqa
    import udata.features.identicon.api  # noqa
    import udata.features.territories.api  # noqa
    import udata.harvest.api  # noqa

    # api.init_app(app)
    app.register_blueprint(apidoc)
    app.register_blueprint(apiv1)

    oauth2.init_app(app)
