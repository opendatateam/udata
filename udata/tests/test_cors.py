from datetime import datetime

from flask import url_for

from udata import assets
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import assert_status


class CorsTest(APITestCase):
    modules = []

    def test_cors_on_allowed_routes(self):
        cors_headers = {
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "GET",
        }

        dataset = DatasetFactory(resources=[ResourceFactory()])

        # API Swagger
        response = self.get(url_for("api.specs"), headers=cors_headers)
        assert_status(response, 200)
        assert "Access-Control-Allow-Origin" in response.headers

        # API Dataset
        response = self.get(url_for("api.dataset", dataset=dataset.id), headers=cors_headers)
        assert_status(response, 200)
        assert "Access-Control-Allow-Origin" in response.headers

        # Resource permalink
        response = self.get(f"/fr/datasets/r/{dataset.resources[0].id}", headers=cors_headers)
        assert_status(response, 404)  # The route is defined in udata-front
        assert "Access-Control-Allow-Origin" in response.headers

        # Oauth
        response = self.get("/oauth/", headers=cors_headers)
        assert_status(response, 404)  # Oauth is defined in udata-front
        assert "Access-Control-Allow-Origin" in response.headers

        # Static
        response = self.get(
            assets.cdn_for("static", filename="my_static.css"), headers=cors_headers
        )
        assert_status(response, 404)  # Not available in APITestCase
        assert "Access-Control-Allow-Origin" in response.headers

    def test_cors_redirects(self):
        dataset = DatasetFactory(title="Old title")
        old_slug = dataset.slug

        # New slug to force a redirect from old slug
        dataset.title = "New title"
        dataset.save()

        response = self.get(url_for("api.dataset", dataset=old_slug))
        assert_status(response, 308)

        response = self.options(
            url_for("api.dataset", dataset=old_slug),
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert_status(response, 204)

    def test_cors_404(self):
        response = self.get(url_for("api.dataset", dataset="unknown-dataset"))
        assert_status(response, 404)

        response = self.options(
            url_for("api.dataset", dataset="unknown-dataset"),
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert_status(response, 204)

    def test_cors_410_with_api_abort(self):
        dataset = DatasetFactory(deleted=datetime.now())

        response = self.get(url_for("api.dataset", dataset=dataset.id))
        assert_status(response, 410)

        response = self.options(
            url_for("api.dataset", dataset=dataset.id),
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert_status(response, 204)
