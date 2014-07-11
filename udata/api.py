# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime

from flask import request, url_for
from flask.ext.restful import Api, Resource, marshal, fields

from udata import search
from udata.utils import multi_to_dict

log = logging.getLogger(__name__)


class UDataApi(Api):
    def make_response(self, data, *args, **kwargs):
        response = super(UDataApi, self).make_response(data, *args, **kwargs)
        #  Remove the content type when there is no content
        if response.status_code == 204 and not response.data:
            response.headers.pop('Content-Type')
        return response

api = UDataApi(prefix='/api')


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

    def post(self):
        form = self.form(request.form, csrf_enabled=False)
        if not form.validate():
            return {'errors': form.errors}, 400
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

    def put(self, **kwargs):
        obj = self.get_or_404(**kwargs)
        form = self.form(request.form, instance=obj, csrf_enabled=False)
        if not form.validate():
            return {'errors': form.errors}, 400
        return marshal(form.save(), self.fields)

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
