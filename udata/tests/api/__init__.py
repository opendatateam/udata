from contextlib import contextmanager
from urllib.parse import urlparse

import pytest
from flask import json

from udata.core.user.factories import UserFactory
from udata.mongo import db
from udata.mongo.document import get_all_models
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
        if not self._user.apikey:
            self._user.generate_api_key()
            self._user.save()
        yield self._user
        self._user = None

    def login(self, user=None):
        """Login a user via session authentication."""
        from flask import current_app
        from flask_principal import Identity, identity_changed

        user = user or UserFactory()
        with self.client.session_transaction() as session:
            # Since flask-security-too 4.0.0, the user.fs_uniquifier is used instead of user.id for auth
            user_id = getattr(user, current_app.login_manager.id_attribute)()
            session["user_id"] = user_id
            session["_fresh"] = True
            session["_id"] = current_app.login_manager._session_identifier_generator()
            current_app.login_manager._update_request_context_with_user(user)
            identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
        self.user = user
        return self.user

    def logout(self):
        """Logout the current user."""
        with self.client.session_transaction() as session:
            del session["user_id"]
            del session["_fresh"]
            del session["_id"]
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
            headers["X-API-KEY"] = kwargs.get("X-API-KEY", self._user.apikey)

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


for code in 200, 201, 204, 400, 401, 403, 404, 410, 500:
    name = "assert{0}".format(code)
    helper = getattr(helpers, name)
    setattr(APITestCaseMixin, name, lambda s, r, h=helper: h(r))


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
        db.connection.drop_database(db_name)

    @pytest.fixture(autouse=True)
    def _clean_db(self, app):
        self.drop_db(app)
        for model in get_all_models():
            # When dropping the database, MongoEngine will keep the collection cached inside
            # `_collection` (in memory). This cache is used to call `ensure_indexes` only on the
            # first call to `_get_collection()`, on subsequent calls the value inside `_collection`
            # is returned without calling `ensure_indexes`.
            # In tests, the first test will have a clean memory state, so MongoEngine will initialise
            # the collection and create the indexes, then the following test, with a clean database (no indexes)
            # will have the collection cached, so MongoEngine will never create the indexes (except if `auto_create_index_on_save`
            # is set on the model, which may be the reason it is present on most of the big models, we may remove it?)
            model._collection = None


class DBTestCase(_CleanDBMixin, TestCase):
    pass


class PytestOnlyDBTestCase(_CleanDBMixin, PytestOnlyTestCase):
    pass


class APITestCase(APITestCaseMixin, DBTestCase):
    pass


class PytestOnlyAPITestCase(APITestCaseMixin, PytestOnlyDBTestCase):
    pass
