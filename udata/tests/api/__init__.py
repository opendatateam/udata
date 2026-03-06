from contextlib import contextmanager
from urllib.parse import urlparse

import pytest
from flask import json
from flask_security.utils import login_user, logout_user, set_request_attr

from udata.core.user.api_tokens import ApiToken
from udata.core.user.factories import UserFactory
from udata.mongo import db
from udata.tests import PytestOnlyTestCase, TestCase, helpers


@pytest.mark.usefixtures("instance_path")
class APITestCaseMixin:
    """
    API Test Case Mixin with integrated API client functionality.

    This mixin provides API testing methods with automatic JSON handling.
    The `get`, `post`, `put`, `patch`, `delete`, and `options` methods
    default to JSON content-type and automatic serialization.
    """

    user = None
    _user = None  # For API key authentication context

    @pytest.fixture(autouse=True)
    def load_api_routes(self, app):
        from udata import api, frontend

        api.init_app(app)
        frontend.init_app(app)

    @pytest.fixture(autouse=True)
    def inject_client(self, app):
        """
        Inject test client for Flask testing.
        """
        self.client = app.test_client()

    @contextmanager
    def api_user(self, user=None):
        """
        Context manager for API key authentication.

        Usage:
            with self.api_user(user) as user:
                response = self.get(url)
        """
        self._user = user or UserFactory()
        token, plaintext = ApiToken.generate(self._user)
        self._api_key = plaintext
        yield self._user
        self._user = None
        self._api_key = None

    def login(self, user=None):
        """Login a user via session authentication."""
        self.user = user or UserFactory()

        login_user(self.user)
        set_request_attr("fs_authn_via", "session")

        return self.user

    def logout(self):
        """Logout the current user."""
        logout_user()
        self.user = None

    def perform(self, verb, url, **kwargs):
        """
        Perform an HTTP request with JSON handling.

        Args:
            verb: HTTP verb (get, post, put, patch, delete, options)
            url: URL to request
            **kwargs: Additional arguments for the request

        Returns:
            Flask test response
        """
        headers = kwargs.pop("headers", {})

        # Only set Content-Type for methods that have a body
        if verb in ("post", "put", "patch", "delete"):
            headers["Content-Type"] = "application/json"

        data = kwargs.get("data")
        if data is not None:
            data = json.dumps(data)
            headers["Content-Length"] = len(data)
            kwargs["data"] = data

        if self._user:
            headers["X-API-KEY"] = kwargs.get("X-API-KEY", self._api_key)

        kwargs["headers"] = headers
        method = getattr(self.client, verb)
        return method(url, **kwargs)

    def get(self, url, *args, **kwargs):
        """Perform a GET request with JSON handling."""
        return self.perform("get", url, *args, **kwargs)

    def post(self, url, data=None, json=True, *args, **kwargs):
        """
        Perform a POST request.

        Args:
            url: URL to request
            data: Data to send (will be JSON-encoded if json=True)
            json: If True, send as JSON (default: True)
            *args, **kwargs: Additional arguments
        """
        if not json:
            return self.client.post(url, data=data or {}, *args, **kwargs)
        return self.perform("post", url, data=data or {}, *args, **kwargs)

    def put(self, url, data=None, json=True, *args, **kwargs):
        """
        Perform a PUT request.

        Args:
            url: URL to request
            data: Data to send (will be JSON-encoded if json=True)
            json: If True, send as JSON (default: True)
            *args, **kwargs: Additional arguments
        """
        if not json:
            return self.client.put(url, data=data or {}, *args, **kwargs)
        return self.perform("put", url, data=data or {}, *args, **kwargs)

    def patch(self, url, data=None, json=True, *args, **kwargs):
        """
        Perform a PATCH request.

        Args:
            url: URL to request
            data: Data to send (will be JSON-encoded if json=True)
            json: If True, send as JSON (default: True)
            *args, **kwargs: Additional arguments
        """
        if not json:
            return self.client.patch(url, data=data or {}, *args, **kwargs)
        return self.perform("patch", url, data=data or {}, *args, **kwargs)

    def delete(self, url, data=None, *args, **kwargs):
        """Perform a DELETE request with JSON handling."""
        return self.perform("delete", url, data=data or {}, *args, **kwargs)

    def options(self, url, data=None, *args, **kwargs):
        """Perform an OPTIONS request with JSON handling."""
        return self.perform("options", url, data=data or {}, *args, **kwargs)

    def assertStatus(self, response, status_code, message=None):
        __tracebackhide__ = True
        helpers.assert_status(response, status_code, message=message)

    def assert200(self, response):
        __tracebackhide__ = True
        helpers.assert200(response)

    def assert201(self, response):
        __tracebackhide__ = True
        helpers.assert201(response)

    def assert204(self, response):
        __tracebackhide__ = True
        helpers.assert204(response)

    def assert400(self, response):
        __tracebackhide__ = True
        helpers.assert400(response)

    def assert401(self, response):
        __tracebackhide__ = True
        helpers.assert401(response)

    def assert403(self, response):
        __tracebackhide__ = True
        helpers.assert403(response)

    def assert404(self, response):
        __tracebackhide__ = True
        helpers.assert404(response)

    def assert410(self, response):
        __tracebackhide__ = True
        helpers.assert410(response)

    def assert500(self, response):
        __tracebackhide__ = True
        helpers.assert500(response)


class _CleanDBMixin:
    """
    This is only for internal use. We shouldn't inherit from this mixin but
    from `DBTestCase` or `PytestOnlyDBTestCase` (or `*APITestCase`)
    This is temporary while we have two hierarchies.
    """

    def drop_db(self, app):
        """Clear the database"""
        parsed_url = urlparse(app.config["MONGODB_HOST"])

        # drop the leading /
        db_name = parsed_url.path[1:]
        # Truncate all documents instead of dropping collections or database.
        # drop_database/drop_collection cause WiredTiger to defer file deletions
        # while MongoEngine immediately recreates collections and indexes via
        # ensure_indexes. This rapid drop/recreate cycle exhausts file descriptors
        # and crashes MongoDB ("Too many open files" → WiredTiger panic).
        # delete_many involves zero file operations: no drops, no creates.
        # Indexes and collections persist across tests, which is fine since
        # the schemas don't change between tests.
        database = db.connection[db_name]
        for collection_name in database.list_collection_names():
            if not collection_name.startswith("system."):
                database[collection_name].delete_many({})

    @pytest.fixture(autouse=True)
    def _clean_db(self, app):
        self.drop_db(app)


class DBTestCase(_CleanDBMixin, TestCase):
    pass


class PytestOnlyDBTestCase(_CleanDBMixin, PytestOnlyTestCase):
    pass


class APITestCase(APITestCaseMixin, DBTestCase):
    pass


class PytestOnlyAPITestCase(APITestCaseMixin, PytestOnlyDBTestCase):
    pass
