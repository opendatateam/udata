import os
import re
from uuid import uuid4

import pytest

from udata.tests.fakes import DataCiteFake, ProConnectFake

# The storages the resources migration is about, and the images, where what S3 serves an SVG
# with matters. The others keep their own tests on the local backend.
S3_TESTED_STORAGES = ("resources", "chunks", "images")


def pytest_configure(config):
    # Each xdist worker gets its own MongoDB database to avoid conflicts
    # when tests drop/recreate the database.
    workerinput = getattr(config, "workerinput", None)
    if workerinput is not None:
        worker_id = workerinput["workerid"]
        from udata import settings

        settings.Testing.MONGODB_HOST_TEST = f"mongodb://localhost:27017/udata_test_{worker_id}"


@pytest.fixture
def rmock():
    """A requests-mock fixture"""
    import requests_mock

    with requests_mock.Mocker() as m:
        m.ANY = requests_mock.ANY
        yield m


@pytest.fixture
def datacite(app, rmock):
    """An in-memory DataCite, wired behind every call to the configured platform."""
    fake = DataCiteFake()
    platform_uri = app.config["DOI_PLATFORM_URI"]
    rmock.put(re.compile(f"^{re.escape(platform_uri)}/dois/"), json=fake.handle_put)
    return fake


@pytest.fixture
def proconnect(app, rmock, monkeypatch):
    """An in-memory ProConnect, registered as udata's OpenID provider."""
    from authlib.integrations.flask_client import OAuth

    from udata.auth import proconnect as proconnect_auth

    fake = ProConnectFake(client_id="udata-test")
    fake.mount(rmock)
    app.config.update(
        PROCONNECT_CLIENT_ID=fake.client_id,
        PROCONNECT_CLIENT_SECRET="secret",
        PROCONNECT_OPENID_CONF_URL=fake.METADATA_URL,
        PROCONNECT_SCOPE="openid email given_name usual_name",
    )
    # A registry of its own: the module-level one keeps the client built for a previous
    # app, or from a local udata.cfg pointing at the real ProConnect.
    monkeypatch.setattr(proconnect_auth, "oauth", OAuth())
    proconnect_auth.init_app(app)
    return fake


@pytest.fixture
def no_ambient_proxy(monkeypatch):
    """Drop the proxy settings exported by the machine.

    requests resolves ``*_proxy``/``no_proxy`` from the environment on every
    request, so whether a test exercises the HTTP stack or a proxy is otherwise
    decided by the developer's shell or the CI image — which does export
    ``no_proxy``.
    """
    for name in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def instance_path(app, tmpdir):
    """Use temporary application instance_path"""
    from udata.core import storages

    app.instance_path = str(tmpdir)
    app.config["FS_ROOT"] = str(tmpdir / "fs")
    # Force local storage:
    for s in "resources", "avatars", "logos", "images", "chunks":
        key = f"{s.upper()}_FS_{{0}}"
        app.config[key.format("BACKEND")] = "local"
        app.config.pop(key.format("ROOT"), None)

    storages.init_app(app)

    return tmpdir


@pytest.fixture
def s3_storages(app, instance_path):
    """Store resources and chunks on S3 instead of the local filesystem.

    Mirrors `instance_path`, which forces every storage to the local backend:
    both rewrite the configuration then reconfigure the storages. Requires a
    running S3 service, so tests using it must be marked with
    `requires_s3_service` (see `udata.tests.helpers`).
    """
    from udata.core import storages

    app.config["FS_S3_ENDPOINT"] = os.environ["UDATA_TEST_S3_ENDPOINT"]
    app.config["FS_S3_REGION"] = os.environ.get("UDATA_TEST_S3_REGION", "us-east-1")
    app.config["FS_S3_ACCESS_KEY"] = os.environ["UDATA_TEST_S3_ACCESS_KEY"]
    app.config["FS_S3_SECRET_KEY"] = os.environ["UDATA_TEST_S3_SECRET_KEY"]
    app.config["FS_S3_CREATE_BUCKET"] = True

    # A bucket set per test: the suite runs on parallel xdist workers, and the
    # backend never removes the buckets it creates.
    suffix = uuid4().hex
    for name in S3_TESTED_STORAGES:
        app.config[f"{name.upper()}_FS_BACKEND"] = "s3"
        app.config[f"{name.upper()}_FS_BUCKET_NAME"] = f"udata-test-{name}-{suffix}"

    storages.init_app(app)

    yield

    for name in S3_TESTED_STORAGES:
        bucket = getattr(storages, name).backend.bucket
        bucket.objects.all().delete()
        bucket.delete()
