# Testing your code

There are three complementary ways of testing your work: unit tests for the backend,
unit tests for the frontend and integration tests.

## Backend unit tests

The easiest way is to run Python tests with [Pytest](https://docs.pytest.org/en/stable/):

```shell
$ pytest
```

You can launch a unique test too:

```shell
$ pytest udata/tests/api/test_me_api.py -k test_get_profile
```

To launch tests with coverage report:

```shell
$ uv sync
$ inv cover
```

With pip (requires pip 25.1+):
```shell
$ pip install --group dev -e .
$ inv cover
```
