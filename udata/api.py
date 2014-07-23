# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime
from functools import wraps

from flask import request, url_for, json, make_response
from flask.ext.restful import Api, Resource, marshal, fields, abort

from udata import search
from udata.auth import current_user, login_user
from udata.frontend import csrf
from udata.utils import multi_to_dict
from udata.core.user.models import User

log = logging.getLogger(__name__)


class UDataApi(Api):
    def secure(self, func):
        '''Enforce authentication on a given method/verb'''
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated():
                return func(*args, **kwargs)

            apikey = request.form.get('apikey') or request.headers.get('X-API-KEY')
            if not apikey:
                self.abort(401)
            try:
                user = User.objects.get(apikey=apikey)
            except User.DoesNotExist:
                # abort(401)
                self.abort(401, 'Invalid API Key')

            if not login_user(user, False):
                self.abort(401, 'Inactive user')
            return func(*args, **kwargs)

        return wrapper

    def abort(self, code=500, message=None, **kwargs):
        if message or kwargs and not 'status' in kwargs:
            kwargs['status'] = code
        if message:
            kwargs['message'] = message
        abort(code, **kwargs)

    def validate(self, form_cls, instance=None):
        form = form_cls(request.form, instance=instance, csrf_enabled=False)
        if not form.validate():
            self.abort(400, errors=form.errors)
        return form


api = UDataApi(prefix='/api', decorators=[csrf.exempt])


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
        if self.search_adapter:
            result = search.query(self.search_adapter, **multi_to_dict(request.args))
            objects = result.get_objects()
        else:
            objects = list(self.model.objects)
        return marshal(objects, self.fields)

    @api.secure
    def post(self):
        form = api.validate(self.form)
        return marshal(form.save(), self.fields), 201


class SingleObjectAPI(object):
    model = None

    def get_or_404(self, **kwargs):
        if self.model.__class__.__name__.lower() in kwargs:
            return kwargs[self.model.__class__.__name__.lower()]
        return self.model.objects.get_or_404(**kwargs)


class ModelAPI(SingleObjectAPI, API):
    fields = None
    form = None

    def get(self, **kwargs):
        obj = self.get_or_404(**kwargs)
        return marshal(obj, self.fields)

    @api.secure
    def put(self, **kwargs):
        obj = self.get_or_404(**kwargs)
        form = api.validate(self.form, obj)
        return marshal(form.save(), self.fields)

    @api.secure
    def delete(self, **kwargs):
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


class SelfUrl(fields.Raw):
    def __init__(self, endpoint, mapper=None):
        super(SelfUrl, self).__init__()
        self.endpoint = endpoint
        self.mapper = mapper or self.default_mapper

    def default_mapper(self, obj):
        return {'id': str(obj.id)}

    def output(self, key, obj):
        return url_for(self.endpoint, _external=True, **self.mapper(obj))

fields.SelfUrl = SelfUrl


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
