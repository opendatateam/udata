# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import urllib

from datetime import datetime
from functools import wraps

from flask import (
    current_app, g, request, url_for, json, make_response, redirect, Blueprint
)
from flask.ext.restplus import Api, Resource, marshal, cors

from udata import search, theme, tracking, models
from udata.app import csrf
from udata.i18n import I18nBlueprint
from udata.auth import (
    current_user, login_user, Permission, RoleNeed, PermissionDenied
)
from udata.utils import multi_to_dict
from udata.core.user.models import User
from udata.sitemap import sitemap

from . import fields, oauth2
from .signals import on_api_call


log = logging.getLogger(__name__)

apiv1 = Blueprint('api', __name__, url_prefix='/api/1')
apidoc = I18nBlueprint('apidoc', __name__)


DEFAULT_PAGE_SIZE = 50
HEADER_API_KEY = 'X-API-KEY'


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
        form = form_cls.from_json(request.json, obj=obj, instance=obj,
                                  csrf_enabled=False)
        if not form.validate():
            self.abort(400, errors=form.errors)
        return form

    def render_ui(self):
        return redirect(url_for('apii18n.apidoc'))

    def search_parser(self, adapter, paginate=True):
        parser = self.parser()
        # q parameter
        parser.add_argument('q', type=str, location='args',
                            help='The search query')
        # Expected facets
        # (ie. I want all facets or I want both tags and licenses facets)
        facets = adapter.facets.keys()
        if facets:
            parser.add_argument('facets', type=str, location='args',
                                choices=['all'] + facets, action='append',
                                help='Selected facets to fetch')
        # Add facets filters arguments
        # (apply a value to a facet ie. tag=value)
        for name, facet in adapter.facets.items():
            parser.add_argument(name, type=str, location='args')
        # Sort arguments
        keys = adapter.sorts.keys()
        choices = keys + ['-' + k for k in keys]
        help_msg = 'The field (and direction) on which sorting apply'
        parser.add_argument('sort', type=str, location='args', choices=choices,
                            help=help_msg)
        if paginate:
            parser.add_argument('page', type=int, location='args',
                                default=0, help='The page to display')
            parser.add_argument('page_size', type=int, location='args',
                                default=20, help='The page size')
        return parser

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

    def resolve_model(self, model):
        '''
        Resolve a model given a name or dict with `class` entry.

        Conventions are resolved too: DatasetFull will resolve as Dataset
        '''
        if not model:
            raise ValueError('Unsupported model specifications')
        if isinstance(model, basestring):
            classname = model
        elif isinstance(model, dict) and 'class' in model:
            classname = model['class']
        else:
            raise ValueError('Unsupported model specifications')

        # Handle Full convention until fields masks make it in
        if classname.endswith('Full'):
            classname = classname[:-4]

        resolved = getattr(models, classname, None)
        if not resolved or not issubclass(resolved, models.db.Document):
            raise ValueError('Model not found')
        return resolved


api = UDataApi(
    apiv1,
    decorators=[csrf.exempt, cors.crossdomain(origin='*', credentials=True)],
    version='1.0', title='uData API',
    description='uData API', default='site',
    default_label='Site global namespace'
)


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
    return name


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


@apidoc.route('/api/')
@apidoc.route('/api/1/')
@api.documentation
def default_api():
    return redirect(url_for('apidoc.swaggerui'))


@apidoc.route('/apidoc/')
def swaggerui():
    return theme.render('apidoc.html', specs_url=api.specs_url)


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
    pass


class ModelListAPI(API):
    model = None
    fields = None
    form = None
    search_adapter = None

    @api.doc(params={})
    def get(self):
        '''List all objects'''
        if self.search_adapter:
            objects = search.query(self.search_adapter,
                                   **multi_to_dict(request.args))
        else:
            objects = list(self.model.objects)
        return marshal_page(objects, self.fields)

    @api.secure
    @api.doc(responses={400: 'Validation error'})
    def post(self):
        '''Create a new object'''
        form = api.validate(self.form)
        return marshal(form.save(), self.fields), 201


class SingleObjectAPI(object):
    model = None

    def get_or_404(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, self.model):
                return value
        return self.model.objects.get_or_404(**kwargs)


@api.doc(responses={404: 'Object not found'})
class ModelAPI(SingleObjectAPI, API):
    fields = None
    form = None

    def get(self, **kwargs):
        '''Get a given object'''
        obj = self.get_or_404(**kwargs)
        return marshal(obj, self.fields)

    @api.secure
    @api.doc(responses={400: 'Validation error'})
    def put(self, **kwargs):
        '''Update a given object'''
        obj = self.get_or_404(**kwargs)
        form = api.validate(self.form, obj)
        return marshal(form.save(), self.fields)

    @api.secure
    @api.doc(model=None, responses={204: 'Object deleted'})
    def delete(self, **kwargs):
        '''Delete a given object'''
        obj = self.get_or_404(**kwargs)
        if hasattr(obj, 'deleted'):
            obj.deleted = datetime.now()
            obj.save()
        else:
            obj.delete()
        return '', 204


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
    import udata.features.territories.api  # noqa
    import udata.harvest.api  # noqa

    # Load plugins API
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.api'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)

    # api.init_app(app)
    app.register_blueprint(apidoc)
    app.register_blueprint(apiv1)

    oauth2.init_app(app)
