import json
from urllib.parse import urljoin

import pytest
import requests
from faker.providers import BaseProvider

from udata.utils import faker, faker_provider

CKAN_URL = "http://localhost:5000"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "ckan_data(fixture): specify the data fixture they rely on. This allows `data`, `result` and `kwargs` fixtures to be populated with the associated data harvest data.",
    )


class CkanError(ValueError):
    pass


class CkanClient:
    BASE_URL = CKAN_URL
    API_URL = f"{BASE_URL}/api/3/action/"
    PACKAGE_LIST_URL = f"{API_URL}package_list"
    PACKAGE_SEARCH_URL = f"{API_URL}package_search"
    PACKAGE_SHOW_URL = f"{API_URL}package_show"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": "dummy_apikey",
        }

    def get(self, url, **kwargs):
        return requests.get(url, headers=self.headers, **kwargs)

    def post(self, url, data, **kwargs):
        return requests.post(url, data=json.dumps(data), headers=self.headers, **kwargs)

    def action_url(self, endpoint):
        path = f"api/3/action/{endpoint}"
        return urljoin(self.BASE_URL, path)

    def action(self, endpoint, data=None, **kwargs):
        url = self.action_url(endpoint)
        if data:
            response = self.post(url, data, params=kwargs)
        else:
            response = self.get(url, params=kwargs)
        if not 200 <= response.status_code < 300:
            raise CkanError(response.text.strip('"'))
        return response.json()


@pytest.fixture(scope="session")
def ckan():
    return CkanClient()


@faker_provider
class UdataCkanProvider(BaseProvider):
    def unique_url(self):
        return f"{faker.uri()}?_={faker.unique_string()}"
