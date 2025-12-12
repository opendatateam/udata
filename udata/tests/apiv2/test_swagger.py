import json

from flask import url_for
from flask_restx import schemas

from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200


class SwaggerBlueprintTest(PytestOnlyAPITestCase):
    def test_swagger_resource_type(self):
        response = self.get(url_for("apiv2.specs"))
        assert200(response)
        swagger = json.loads(response.data)
        expected = swagger["paths"]["/datasets/{dataset}/resources/"]
        expected = expected["get"]["responses"]["200"]["schema"]["$ref"]
        assert expected == "#/definitions/ResourcePage"

    def test_swagger_specs_validate(self):
        response = self.get(url_for("apiv2.specs"))
        try:
            schemas.validate(response.json)
        except schemas.SchemaValidationError as e:
            print(e.errors)
            raise
