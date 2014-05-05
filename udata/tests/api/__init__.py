# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import api
from udata.core import storages
from udata.core.storages.views import blueprint

from .. import TestCase, WebTestMixin, SearchTestMixin


class APITestCase(WebTestMixin, SearchTestMixin, TestCase):
    def create_app(self):
        app = super(APITestCase, self).create_app()
        api.init_app(app)
        storages.init_app(app)
        app.register_blueprint(blueprint)
        return app
