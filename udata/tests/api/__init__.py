# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager

from udata import api
from udata.core import storages
from udata.core.storages.views import blueprint

from .. import TestCase, WebTestMixin, SearchTestMixin
from ..factories import UserFactory


class APITestCase(WebTestMixin, SearchTestMixin, TestCase):
    def create_app(self):
        app = super(APITestCase, self).create_app()
        api.init_app(app)
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

    def inject_apikey(self, verb, *args, **kwargs):
        if getattr(self, '_api_user', None):
            headers = kwargs.pop('headers', {})
            headers['X-API-KEY'] = kwargs.get('X-API-KEY', self._api_user.apikey)
            kwargs['headers'] = headers
        method = getattr(super(APITestCase, self), verb)
        return method(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.inject_apikey('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.inject_apikey('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.inject_apikey('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.inject_apikey('delete', *args, **kwargs)
