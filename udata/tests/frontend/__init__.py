# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import re

from udata.tests import TestCase, WebTestMixin, SearchTestMixin

from udata import frontend, api


class FrontTestCase(WebTestMixin, SearchTestMixin, TestCase):
    def create_app(self):
        app = super(FrontTestCase, self).create_app()
        api.init_app(app)
        frontend.init_app(app)
        return app

    def get_json_ld(self, response):
        # In the pattern below, we extract the content of the JSON-LD script
        # The first ? is used to name the extracted string
        # The second ? is used to express the non-greediness of the extraction
        pattern = ('<script id="json_ld" type="application/ld\+json">'
                   '(?P<json_ld>[\s\S]*?)'
                   '</script>')
        search = re.search(pattern, response.data)
        self.assertIsNotNone(search, (pattern, response.data))
        json_ld = search.group('json_ld')
        return json.loads(json_ld)
