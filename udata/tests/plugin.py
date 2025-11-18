import shlex

import pytest

from .helpers import assert_command_ok


@pytest.fixture(name="cli")
def cli_fixture(app):
    def mock_runner(*args, **kwargs):
        from udata.commands import cli

        if len(args) == 1 and " " in args[0]:
            args = shlex.split(args[0])
        runner = app.test_cli_runner()
        result = runner.invoke(cli, args, catch_exceptions=False)
        if kwargs.get("check", True):
            assert_command_ok(result)
        return result

    return mock_runner


def rmock():
    """A requests-mock fixture"""
    import requests_mock

    with requests_mock.Mocker() as m:
        m.ANY = requests_mock.ANY
        yield m


@pytest.fixture
def instance_path(app, tmpdir):
    """Use temporary application instance_path"""
    from udata.core import storages

    app.instance_path = str(tmpdir)
    app.config["FS_ROOT"] = str(tmpdir / "fs")
    # Force local storage:
    for s in "resources", "avatars", "logos", "images", "chunks", "tmp":
        key = "{0}_FS_{{0}}".format(s.upper())
        app.config[key.format("BACKEND")] = "local"
        app.config.pop(key.format("ROOT"), None)

    storages.init_app(app)

    return tmpdir
