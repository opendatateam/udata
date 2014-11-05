# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime
from functools import wraps

from flask import request, url_for, json, make_response, redirect
from flask.ext.restplus import Api, Resource, marshal

from udata import search
from udata.i18n import I18nBlueprint
from udata.auth import current_user, login_user, Permission, RoleNeed
from udata.frontend import csrf, render
from udata.utils import multi_to_dict
from udata.core.user.models import User

from . import oauth2

log = logging.getLogger(__name__)

bp = I18nBlueprint('apii18n', __name__)


DEFAULT_PAGE_SIZE = 50
HEADER_API_KEY = 'X-API-KEY'


class UDataApi(Api):
    def __init__(self, **kwargs):
        kwargs['decorators'] = [self.authentify] + (kwargs.pop('decorators', []) or [])
        super(UDataApi, self).__init__(**kwargs)
        self.authorizations = {'apikey': {'type': 'apiKey', 'passAs': 'header', 'keyname': HEADER_API_KEY}}

    def secure(self, func):
        '''Enforce authentication on a given method/verb and optionnaly check a given permission'''
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
        self._handle_api_doc(func, {'authorizations': 'apikey'})

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated():
                self.abort(401)

            if permission is not None:
                with permission.require(403):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    def authentify(self, func):
        '''Authentify the user if credentials are given'''
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated():
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

    def validate(self, form_cls, instance=None):
        '''Validate a form from the request and handle errors'''
        form = form_cls.from_json(request.json, instance=instance, csrf_enabled=False)
        if not form.validate():
            self.abort(400, errors=form.errors)
        return form

    def render_ui(self):
        return redirect(url_for('apii18n.apidoc'))


api = UDataApi(prefix='/api/1', decorators=[csrf.exempt],
    version='1.0', title='uData API',
    description='uData API', default='site', default_label='Site global namespace'
)

refs = api.namespace('references', 'References lists')

from . import fields  # Needs to be imported after api declaration


@api.representation('application/json')
def output_json(data, code, headers=None):
    '''Use Flask JSON to serialize'''
    resp = make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


@bp.route('/api/')
def default_api():
    return redirect(url_for('apii18n.apidoc'))


@bp.route('/apidoc/')
def apidoc():
    return render('apidoc.html', api_endpoint=api.endpoint, specs_url=api.specs_url)


@bp.route('/apidoc/images/throbber.gif')
def fix_apidoc_throbber():
    return redirect(url_for('api.fix_throbber'))


class API(Resource):  # Avoid name collision as resource is a core model
    pass


class ModelListAPI(API):
    model = None
    fields = None
    form = None
    search_adapter = None

    def get(self):
        '''List all objects'''
        if self.search_adapter:
            objects = search.query(self.search_adapter, **multi_to_dict(request.args))
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


def pager(page_fields):
    pager_fields = {
        'data': api.as_list(fields.Nested(page_fields, attribute='objects', description='The page data')),
        'page': fields.Integer(description='The current page', required=True, min=0),
        'page_size': fields.Integer(description='The page size used for pagination', required=True, min=0),
        'total': fields.Integer(description='The total paginated items', required=True, min=0),
        'next_page': fields.NextPageUrl(description='The next page URL if exists'),
        'previous_page': fields.PreviousPageUrl(description='The previous page URL if exists'),
    }
    return pager_fields


def marshal_page(page, page_fields):
    return marshal(page, pager(page_fields))


def marshal_page_with(func):
    pass


def init_app(app):
    # Load all core APIs
    import udata.core.spatial.api
    import udata.core.metrics.api
    import udata.core.user.api
    import udata.core.dataset.api
    import udata.core.reuse.api
    import udata.core.organization.api
    import udata.core.suggest.api
    import udata.core.followers.api
    import udata.core.jobs.api

    # Load plugins API
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.api'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)

    api.init_app(app)
    app.register_blueprint(bp)

    oauth2.init_app(app)
