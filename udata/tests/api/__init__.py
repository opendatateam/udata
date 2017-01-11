# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager

from flask import json

from udata.core import storages
from udata.core.storages.views import blueprint

from udata.core.user.factories import UserFactory
from ..frontend import FrontTestCase


class APITestCase(FrontTestCase):
    def create_app(self):
        app = super(APITestCase, self).create_app()
        storages.init_app(app)
        app.register_blueprint(blueprint)
        return app

    @contextmanager
    def api_user(self, user=None):
        self._api_user = user or UserFactory()
        if not self._api_user.apikey:
            self._api_user.generate_api_key()
            self._api_user.save()
        yield self._api_user

    def perform(self, verb, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['Content-Type'] = 'application/json'

        data = kwargs.get('data')
        if data is not None:
            data = json.dumps(data)
            headers['Content-Length'] = len(data)
            kwargs['data'] = data

        if getattr(self, '_api_user', None):
            headers['X-API-KEY'] = kwargs.get('X-API-KEY',
                                              self._api_user.apikey)

        kwargs['headers'] = headers
        method = getattr(super(APITestCase, self), verb)
        return method(url, **kwargs)

    def get(self, url, client=None, *args, **kwargs):
        return self.perform('get', url, client=client, *args, **kwargs)

    def post(self, url, data=None, client=None, json=True, *args, **kwargs):
        if not json:
            return super(APITestCase, self).post(
                url, data or {}, client=client, *args, **kwargs)
        return self.perform('post', url, data=data or {}, client=client,
                            *args, **kwargs)

    def put(self, url, data=None, client=None, json=True, *args, **kwargs):
        if not json:
            return super(APITestCase, self).put(
                url, data or {}, client=client, *args, **kwargs)
        return self.perform('put', url, data=data or {}, client=client,
                            *args, **kwargs)

    def delete(self, url, data=None, client=None, *args, **kwargs):
        return self.perform('delete', url, data=data or {}, client=client,
                            *args, **kwargs)
