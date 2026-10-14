# Testing your code

udata is a Python backend, so its test suite is a [Pytest](https://docs.pytest.org/en/stable/)
suite. Run it all with:

```shell
$ uv run pytest
```

You can launch a unique test too:

```shell
$ uv run pytest udata/tests/api/test_me_api.py -k test_get_profile
```

To launch tests with coverage report:

```shell
$ uv run inv cover
```

If you installed with `pip` instead, activate the virtualenv (`source .venv/bin/activate`) and
drop the `uv run` prefix.

## End-to-end tests

The web interface lives in [cdata][], which runs its own Playwright suite against a real udata
started from this repository. A change here that alters the API can break it: see
[cdata's CI workflow][cdata-ci] for the exact setup it expects.

[cdata]: https://github.com/datagouv/cdata
[cdata-ci]: https://github.com/datagouv/cdata/blob/main/.github/workflows/ci.yml
