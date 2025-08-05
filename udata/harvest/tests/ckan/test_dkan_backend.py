import json
import os
from datetime import datetime

import pytest

from udata.app import create_app
from udata.core.organization.factories import OrganizationFactory
from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.models import Dataset
from udata.settings import Defaults, Testing
from udata.tests.plugin import drop_db


def data_path(filename):
    """Get a test data path"""
    return os.path.join(os.path.dirname(__file__), "data", filename)


class DkanSettings(Testing):
    PLUGINS = ["dkan"]


@pytest.fixture(scope="module")
def app(request):
    """Create an udata app once for the module."""
    app = create_app(Defaults, override=DkanSettings)
    with app.app_context():
        drop_db(app)
    yield app
    with app.app_context():
        drop_db(app)


def test_dkan_french_w_license(app, rmock):
    """CKAN Harvester should accept the minimum dataset payload"""
    DKAN_URL = "https://harvest.me/"
    API_URL = "{}api/3/action/".format(DKAN_URL)
    PACKAGE_LIST_URL = "{}package_list".format(API_URL)
    PACKAGE_SHOW_URL = "{}package_show".format(API_URL)

    with open(data_path("dkan-french-w-license.json")) as ifile:
        data = json.loads(ifile.read())

    org = OrganizationFactory()
    source = HarvestSourceFactory(backend="dkan", url=DKAN_URL, organization=org)
    rmock.get(
        PACKAGE_LIST_URL,
        json={"success": True, "result": ["fake-name"]},
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    rmock.get(
        PACKAGE_SHOW_URL, json=data, status_code=200, headers={"Content-Type": "application/json"}
    )
    actions.run(source)
    source.reload()
    assert source.get_last_job().status == "done"

    datasets = Dataset.objects.filter(organization=org)
    assert len(datasets) > 0

    dataset = datasets.get(**{"harvest__remote_id": "04be6288-696d-4331-850d-a144871a7e3a"})
    assert dataset.harvest.created_at == datetime(2019, 12, 10, 0, 0)
    assert dataset.harvest.modified_at == datetime(2019, 9, 30, 0, 0)
    assert len(dataset.resources) == 2
    assert "xlsx" in [r.format for r in dataset.resources]
