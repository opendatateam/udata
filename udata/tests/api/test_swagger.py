import json

from flask import url_for
from flask_restx import schemas

from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200


class SwaggerBlueprintTest(PytestOnlyAPITestCase):
    def test_swagger_resource_type(self):
        response = self.get(url_for("api.specs"))
        assert200(response)
        swagger = json.loads(response.data)
        expected = swagger["paths"]["/datasets/{dataset}/resources/"]
        expected = expected["put"]["responses"]["200"]["schema"]["type"]
        assert expected == "array"

    def test_swagger_specs_validate(self):
        response = self.get(url_for("api.specs"))
        try:
            schemas.validate(response.json)
        except schemas.SchemaValidationError as e:
            print(e.errors)
            raise

    def test_swagger_declares_https_scheme(self):
        response = self.get(url_for("api.specs"))
        assert200(response)
        assert response.json["schemes"] == ["https"]

    def test_swagger_documents_filtering_arguments(self):
        """Endpoints filtering or paginating their results declare the arguments they read."""
        response = self.get(url_for("api.specs"))
        paths = response.json["paths"]
        expectations = {
            "/organizations/{org}/catalog": {"page", "page_size"},
            "/organizations/{org}/contacts/": {"page", "page_size"},
            "/users/{user}/contacts/": {"page", "page_size"},
            "/transfer/": {"subject", "subject_type", "recipient", "status"},
        }
        for path, expected in expectations.items():
            documented = {param["name"] for param in paths[path]["get"]["parameters"]}
            assert expected <= documented, f"{path} misses {expected - documented}"
