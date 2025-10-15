from contextlib import contextmanager
from urllib.parse import urlparse

import pytest

from udata.mongo import db
from udata.mongo.document import get_all_models
from udata.tests import PytestOnlyTestCase, TestCase, helpers


@pytest.mark.usefixtures("instance_path")
class APITestCaseMixin:
    """
    See explanation about `get`, `post` overrides in :TestClientOverride

    (switch from `data` in kwargs to `data` in args to avoid doing `data=data` and default to `json=True`)
    """

    user = None

    @pytest.fixture(autouse=True)
    def load_api_routes(self, app):
        from udata import api, frontend

        api.init_app(app)
        frontend.init_app(app)

    @pytest.fixture(autouse=True)
    def inject_api(self, api):
        """
        Inject API test client for compatibility with legacy tests.
        """
        self.api = api

    @pytest.fixture(autouse=True)
    def inject_client(self, client):
        """
        Inject test client for compatibility with Flask-Testing.
        """
        self.client = client

    @contextmanager
    def api_user(self, user=None):
        with self.api.user(user) as user:
            yield user

    def login(self, user=None):
        self.user = self.client.login(user)
        return self.user

    def get(self, url, *args, **kwargs):
        return self.api.get(url, *args, **kwargs)

    def post(self, url, data=None, json=True, *args, **kwargs):
        return self.api.post(url, data=data, json=json, *args, **kwargs)

    def put(self, url, data=None, json=True, *args, **kwargs):
        return self.api.put(url, data=data, json=json, *args, **kwargs)

    def patch(self, url, data=None, json=True, *args, **kwargs):
        return self.api.patch(url, data=data, json=json, *args, **kwargs)

    def delete(self, url, data=None, *args, **kwargs):
        return self.api.delete(url, data=data, *args, **kwargs)

    def options(self, url, data=None, *args, **kwargs):
        return self.api.options(url, data=data, *args, **kwargs)

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
