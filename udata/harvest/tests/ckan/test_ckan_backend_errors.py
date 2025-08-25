import pytest

from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
    pytest.mark.options(PLUGINS=["ckan"]),
]

CKAN_URL = "https://harvest.me/"
API_URL = "{}api/3/action/package_list".format(CKAN_URL)

# We test against success and error status code
# because CKAN API always return 200
# but some other cases may happen outside the API
STATUS_CODE = (400, 500)


@pytest.mark.parametrize("code", STATUS_CODE)
def test_html_error(rmock, code):
    # Happens with wrong source URL (html is returned instead of json)
    html = "<html><body>Error</body></html>"
    source = HarvestSourceFactory(backend="ckan", url=CKAN_URL)

    rmock.get(API_URL, text=html, status_code=code, headers={"Content-Type": "text/html"})

    actions.run(source)

    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 0
    assert len(job.errors) == 1
    error = job.errors[0]
    # HTML is detected and does not clutter the message
    assert html not in error.message


@pytest.mark.parametrize("code", STATUS_CODE)
def test_plain_text_error(rmock, code):
    source = HarvestSourceFactory(backend="ckan", url=CKAN_URL)

    rmock.get(
        API_URL, text='"Some error"', status_code=code, headers={"Content-Type": "text/plain"}
    )

    actions.run(source)

    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 0
    assert len(job.errors) == 1
    error = job.errors[0]
    # Raw quoted string is properly unquoted
    http_message = "Server Error" if code == 500 else "Client Error"
    assert (
        error.message
        == f"{code} {http_message}: None for url: https://harvest.me/api/3/action/package_list"
    )


def test_200_plain_text_error(rmock):
    source = HarvestSourceFactory(backend="ckan", url=CKAN_URL)

    rmock.get(API_URL, text='"Some error"', status_code=200, headers={"Content-Type": "text/plain"})

    actions.run(source)

    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 0
    assert len(job.errors) == 1
    error = job.errors[0]
    # Raw quoted string is properly unquoted
    assert error.message == "Some error"


def test_standard_api_json_error(rmock):
    json = {"success": False, "error": "an error"}
    source = HarvestSourceFactory(backend="ckan", url=CKAN_URL)

    rmock.get(API_URL, json=json, status_code=200, headers={"Content-Type": "application/json"})

    actions.run(source)

    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 0
    assert len(job.errors) == 1
    error = job.errors[0]
    assert error.message == "an error"


def test_standard_api_json_error_with_details(rmock):
    json = {
        "success": False,
        "error": {
            "message": "an error",
        },
    }
    source = HarvestSourceFactory(backend="ckan", url=CKAN_URL)

    rmock.get(API_URL, json=json, status_code=200, headers={"Content-Type": "application/json"})

    actions.run(source)

    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 0
    assert len(job.errors) == 1
    error = job.errors[0]
    assert error.message == "an error"


def test_standard_api_json_error_with_details_and_type(rmock):
    json = {
        "success": False,
        "error": {
            "message": "Access denied",
            "__type": "Authorization Error",
        },
    }
    source = HarvestSourceFactory(backend="ckan", url=CKAN_URL)

    rmock.get(API_URL, json=json, status_code=200, headers={"Content-Type": "application/json"})

    actions.run(source)

    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 0
    assert len(job.errors) == 1
    error = job.errors[0]
    assert error.message == "Authorization Error: Access denied"
