# Testing your code

There are three complementary ways of testing your work: unit tests for the backend,
unit tests for the frontend and integration tests.

## Test middlewares

If you need to use an alternative Mongo instance during tests, you can provide
the alternate urls in your `udata.cfg` with `MONGODB_HOST_TEST`.

**E.g.**: To make use of the tmpfs based middleware provided by docker compose, use:

```python
MONGODB_HOST_TEST = 'mongodb://localhost:27018/udata'
```

And then start docker compose with the test profile:

```shell
$ docker compose --profile test up
```

This will start a MongoDB extra service, tmpfs based and your tests will
make use of it and run faster.


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
