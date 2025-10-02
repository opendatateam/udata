from uuid import uuid4

from flask import url_for

from udata.core.dataset.factories import DatasetFactory, ResourceFactory

from . import FrontTestCase


class ErrorHandlersTest(FrontTestCase):
    def test_404_page_html(self):
        """Test that a 404 error displays the custom 404 HTML page"""
        # Request a non-existent page
        response = self.get("/this-page-does-not-exist")

        # Check that we get a 404 status code
        assert response.status_code == 404

        # Check that the custom 404 template is rendered
        html = response.data.decode("utf-8")
        assert "404" in html
        assert "Page not found" in html or "page you are looking for does not exist" in html.lower()

        # Check that there's a link back to the homepage
        assert "Back to home" in html or "home" in html.lower()

    def test_resource_redirect_404_html(self):
        """Test that resource redirect returns HTML 404 when HTML is requested"""
        # Use a UUID that doesn't exist
        non_existent_uuid = uuid4()

        # Request the resource redirect endpoint with HTML accept header
        response = self.get(
            url_for("api.resource_redirect", id=non_existent_uuid),
            headers={"Accept": "text/html"}
        )

        # Check that we get a 404 status code
        assert response.status_code == 404

        # Check that the response is HTML (not JSON)
        assert "text/html" in response.content_type

        # Check that the custom 404 template is rendered
        html = response.data.decode("utf-8")
        assert "404" in html
        assert "Page not found" in html or "page you are looking for does not exist" in html.lower()

    def test_404_page_json(self):
        """Test that a 404 error returns JSON when requested"""
        # Request a non-existent page with JSON accept header
        response = self.get(
            "/this-page-does-not-exist",
            headers={"Accept": "application/json"}
        )

        # Check that we get a 404 status code
        assert response.status_code == 404

        # Check that the response is JSON
        assert response.content_type == "application/json"

        # Check the JSON response content
        data = response.json
        assert data["error"] == "Not found"
        assert data["status"] == 404

    def test_api_resource_redirect_404_json(self):
        """Test that API resource redirect returns 404 JSON when resource doesn't exist"""
        # Use a UUID that doesn't exist
        non_existent_uuid = uuid4()

        response = self.get(url_for("api.resource_redirect", id=non_existent_uuid))
        assert response.status_code == 404

        # Check that the response is JSON (Flask-RESTX returns JSON by default for API routes)
        assert response.content_type == "application/json"
