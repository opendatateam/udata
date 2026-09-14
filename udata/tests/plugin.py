import os
from uuid import uuid4

import pytest

# The storages the resources migration is about. The others keep their own
# tests on the local backend.
S3_TESTED_STORAGES = ("resources", "chunks")


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
        key = "{0}_FS_{{0}}".format(s.upper())
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
