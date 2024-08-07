from contextlib import contextmanager

import pytest

from ..frontend import FrontTestCase


@pytest.mark.usefixtures("instance_path")
class APITestCase(FrontTestCase):
    @pytest.fixture(autouse=True)
    def inject_api(self, api):
        """
        Inject API test client for compatibility with legacy tests.
        """
        self.api = api

    @contextmanager
    def api_user(self, user=None):
        with self.api.user(user) as user:
            yield user

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
