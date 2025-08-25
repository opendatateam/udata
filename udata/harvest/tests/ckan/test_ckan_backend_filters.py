import urllib

import pytest

from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.utils import faker

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
    pytest.mark.options(PLUGINS=["ckan"]),
]


def test_include_org_filter(ckan, rmock):
    source = HarvestSourceFactory(
        backend="ckan",
        url=ckan.BASE_URL,
        config={"filters": [{"key": "organization", "value": "organization_name"}]},
    )

    rmock.get(
        ckan.PACKAGE_SEARCH_URL,
        json={"success": True, "result": {"results": []}},
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

    actions.run(source)
    source.reload()

    assert rmock.call_count == 1
    params = {"q": "organization:organization_name", "rows": 1000}
    assert rmock.last_request.url == f"{ckan.PACKAGE_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def test_exclude_org_filter(ckan, rmock):
    source = HarvestSourceFactory(
        backend="ckan",
        url=ckan.BASE_URL,
        config={
            "filters": [{"key": "organization", "value": "organization_name", "type": "exclude"}]
        },
    )

    rmock.get(
        ckan.PACKAGE_SEARCH_URL,
        json={"success": True, "result": {"results": []}},
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

    actions.run(source)
    source.reload()

    assert rmock.call_count == 1

    params = {"q": "-organization:organization_name", "rows": 1000}
    assert rmock.last_request.url == f"{ckan.PACKAGE_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def test_tag_filter(ckan, rmock):
    tag = faker.word()
    source = HarvestSourceFactory(
        backend="ckan", url=ckan.BASE_URL, config={"filters": [{"key": "tags", "value": tag}]}
    )

    rmock.get(
        ckan.PACKAGE_SEARCH_URL,
        json={"success": True, "result": {"results": []}},
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

    actions.run(source)
    source.reload()

    assert rmock.call_count == 1
    params = {"q": f"tags:{tag}", "rows": 1000}
    assert rmock.last_request.url == f"{ckan.PACKAGE_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def test_exclude_tag_filter(ckan, rmock):
    tag = faker.word()
    source = HarvestSourceFactory(
        backend="ckan",
        url=ckan.BASE_URL,
        config={"filters": [{"key": "tags", "value": tag, "type": "exclude"}]},
    )

    rmock.get(
        ckan.PACKAGE_SEARCH_URL,
        json={"success": True, "result": {"results": []}},
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

    actions.run(source)
    source.reload()

    assert rmock.call_count == 1
    params = {"q": f"-tags:{tag}", "rows": 1000}
    assert rmock.last_request.url == f"{ckan.PACKAGE_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def test_can_have_multiple_filters(ckan, rmock):
    source = HarvestSourceFactory(
        backend="ckan",
        url=ckan.BASE_URL,
        config={
            "filters": [
                {"key": "organization", "value": "organization_name"},
                {"key": "tags", "value": "tag-2", "type": "exclude"},
            ]
        },
    )

    rmock.get(
        ckan.PACKAGE_SEARCH_URL,
        json={"success": True, "result": {"results": []}},
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

    actions.run(source)
    source.reload()

    assert rmock.call_count == 1
    params = {"q": "organization:organization_name AND -tags:tag-2", "rows": 1000}
    assert rmock.last_request.url == f"{ckan.PACKAGE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
