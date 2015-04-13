# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tests import TestCase, WebTestMixin, SearchTestMixin

from udata import frontend, api


class FrontTestCase(WebTestMixin, SearchTestMixin, TestCase):
    def create_app(self):
        app = super(FrontTestCase, self).create_app()
        api.init_app(app)
        frontend.init_app(app)
        return app
