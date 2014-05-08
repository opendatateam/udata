# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import request
from flask.ext.restful import Api, Resource, marshal, fields

from udata import search
from udata.core import MODULES
from udata.utils import multi_to_dict

log = logging.getLogger(__name__)


class UDataApi(Api):
    def make_response(self, data, *args, **kwargs):
        response = super(UDataApi, self).make_response(data, *args, **kwargs)
        #  Remove the content type when there is no content
        if response.status_code == 204:
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
        obj.delete()
        return '', 204


def init_app(app):
    # Load all core APIs
    for module in MODULES:
        try:
            __import__('udata.core.{0}.api'.format(module))
        except ImportError as e:
            pass
        except Exception as e:
            log.error('Unable to import %s: %s', module, e)

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
