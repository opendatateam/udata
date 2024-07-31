from datetime import datetime

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import assert_status


class CorsTest(APITestCase):
    modules = []

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
