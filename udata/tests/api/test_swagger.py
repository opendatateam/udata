# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from flask import url_for
from flask_restplus import schemas

from udata.tests.helpers import assert200


class SwaggerBlueprintTest:
    modules = []

    def test_swagger_resource_type(self, api):
        response = api.get(url_for('api.specs'))
        assert200(response)
        swagger = json.loads(response.data)
        expected = swagger['paths']['/datasets/{dataset}/resources/']
        expected = expected['put']['responses']['200']['schema']['type']
        assert expected == 'array'

    def test_swagger_specs_validate(self, api):
        response = api.get(url_for('api.specs'))
        try:
            schemas.validate(response.json)
        except schemas.SchemaValidationError as e:
            print(e.errors)
            raise
