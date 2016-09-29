# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from . import APITestCase


class SwaggerBlueprintTest(APITestCase):

    def test_swagger_resource_type(self):

        response = self.get('api/1/swagger.json')
        self.assert200(response)
        swagger = json.loads(response.data)
        expected = swagger['paths']['/datasets/{dataset}/resources/']
        expected = expected['put']['responses']['200']['schema']['type']
        self.assertEquals(expected, 'array')
