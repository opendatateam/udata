from datetime import datetime

import pytest
from flask import url_for

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import assert_status

TRUSTED_ORIGIN = "https://www.data.gouv.fr"
UNTRUSTED_ORIGIN = "https://evil.example.com"


class CorsTest(APITestCase):
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
        response = self.get(f"/datasets/r/{dataset.resources[0].id}", headers=cors_headers)
        assert_status(response, 404)  # The route is defined in cdata (formerly udata-front)
        assert "Access-Control-Allow-Origin" in response.headers

        # Oauth
        response = self.get("/oauth/", headers=cors_headers)
        assert_status(response, 404)  # Oauth is defined in cdata (formerly udata-front)
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

    @pytest.mark.options(CDATA_BASE_URL=TRUSTED_ORIGIN + "/", CORS_ALLOWED_ORIGINS=[])
    def test_cors_credentials_only_for_trusted_origin(self):
        """An untrusted origin must never get credentials, only anonymous `*`.

        Reflecting an arbitrary origin together with `Allow-Credentials: true`
        would let any website read a logged-in user's private data using their
        session cookie.
        """
        dataset = DatasetFactory()
        url = url_for("api.dataset", dataset=dataset.id)

        # Trusted front-end (derived from CDATA_BASE_URL): credentialed access.
        response = self.get(url, headers={"Origin": TRUSTED_ORIGIN})
        assert_status(response, 200)
        assert response.headers["Access-Control-Allow-Origin"] == TRUSTED_ORIGIN
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

        # Any other origin: anonymous access only, never credentials.
        response = self.get(url, headers={"Origin": UNTRUSTED_ORIGIN})
        assert_status(response, 200)
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Credentials" not in response.headers

    @pytest.mark.options(CDATA_BASE_URL=None, CORS_ALLOWED_ORIGINS=[TRUSTED_ORIGIN])
    def test_cors_credentials_for_explicit_allowed_origin(self):
        dataset = DatasetFactory()
        url = url_for("api.dataset", dataset=dataset.id)

        response = self.get(url, headers={"Origin": TRUSTED_ORIGIN})
        assert response.headers["Access-Control-Allow-Origin"] == TRUSTED_ORIGIN
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    @pytest.mark.options(CDATA_BASE_URL=TRUSTED_ORIGIN + "/", CORS_ALLOWED_ORIGINS=[])
    def test_cors_preflight_credentials_only_for_trusted_origin(self):
        dataset = DatasetFactory()
        url = url_for("api.dataset", dataset=dataset.id)
        preflight_headers = {"Access-Control-Request-Method": "POST"}

        response = self.options(url, headers={"Origin": TRUSTED_ORIGIN, **preflight_headers})
        assert_status(response, 204)
        assert response.headers["Access-Control-Allow-Origin"] == TRUSTED_ORIGIN
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

        response = self.options(url, headers={"Origin": UNTRUSTED_ORIGIN, **preflight_headers})
        assert_status(response, 204)
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Credentials" not in response.headers
