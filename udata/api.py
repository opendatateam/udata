# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime
from functools import wraps

from flask import request, url_for, json, make_response, redirect
from flask.ext.restplus import Api, Resource, marshal, fields, reqparse

from werkzeug.datastructures import MultiDict

from udata import search
from udata.i18n import I18nBlueprint
from udata.auth import current_user, login_user
from udata.frontend import csrf, render
from udata.utils import multi_to_dict
from udata.core.user.models import User

log = logging.getLogger(__name__)

bp = I18nBlueprint('apii18n', __name__)


DEFAULT_PAGE_SIZE = 50


class UDataApi(Api):
    def secure(self, func):
        '''Enforce authentication on a given method/verb'''
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated():
                return func(*args, **kwargs)

            apikey = request.headers.get('X-API-KEY')
            if not apikey:
                self.abort(401)
            try:
                user = User.objects.get(apikey=apikey)
            except User.DoesNotExist:
                self.abort(401, 'Invalid API Key')

            if not login_user(user, False):
                self.abort(401, 'Inactive user')
            return func(*args, **kwargs)

        return wrapper

    def validate(self, form_cls, instance=None):
        '''Validate a form from the request and handle errors'''
        form = form_cls(MultiDict(request.json), instance=instance, csrf_enabled=False)
        if not form.validate():
            self.abort(400, errors=form.errors)
        return form

    def render_ui(self):
        return redirect(url_for('apii18n.apidoc'))


api = UDataApi(prefix='/api', decorators=[csrf.exempt],
    version='1.0', title='uData API',
    description='Bla bla bla'
)


@bp.route('/apidoc/')
def apidoc():
    return render('apidoc.html', api_endpoint=api.endpoint, specs_url=api.specs_url)


@api.representation('application/json')
def output_json(data, code, headers=None):
    '''Use Flask JSON to serialize'''
    resp = make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


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
    def delete(self, **kwargs):
        '''Delete a given object'''
        obj = self.get_or_404(**kwargs)
        if hasattr(obj, 'deleted'):
            obj.deleted = datetime.now()
            obj.save()
        else:
            obj.delete()
        return '', 204


class ISODateTime(fields.Raw):
    def format(self, value):
        return value.isoformat()

fields.ISODateTime = ISODateTime


class UrlFor(fields.Raw):
    def __init__(self, endpoint, mapper=None):
        super(UrlFor, self).__init__()
        self.endpoint = endpoint
        self.mapper = mapper or self.default_mapper

    def default_mapper(self, obj):
        return {'id': str(obj.id)}

    def output(self, key, obj):
        return url_for(self.endpoint, _external=True, **self.mapper(obj))

fields.UrlFor = UrlFor


class NextPageUrl(fields.Raw):
    def output(self, key, obj):
        if not obj.has_next:
            return None
        args = request.args.copy()
        args['page'] = obj.page + 1
        return url_for(request.endpoint, _external=True, **args)


class PreviousPageUrl(fields.Raw):
    def output(self, key, obj):
        if not obj.has_prev:
            return None
        args = request.args.copy()
        args['page'] = obj.page - 1
        return url_for(request.endpoint, _external=True, **args)


def marshal_page(page, page_fields):
    pager_fields = {
        'data': fields.Nested(page_fields, attribute='objects'),
        'page': fields.Integer,
        'page_size': fields.Integer,
        'total': fields.Integer,
        'next_page': NextPageUrl,
        'previous_page': PreviousPageUrl,
    }
    return marshal(page, pager_fields)


def marshal_page_with(func):
    pass


def init_app(app):
    # Load all core APIs
    import udata.core.metrics.api
    import udata.core.user.api
    import udata.core.dataset.api
    import udata.core.reuse.api
    import udata.core.organization.api
    import udata.core.suggest.api
    import udata.core.followers.api

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
