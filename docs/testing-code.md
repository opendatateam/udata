# Testing your code

There a three complementary ways of testing your work: unit tests for the backend, unit tests for the frontend and integration tests.

## Backend unit tests

The easiest way is to run Python tests with [nosetest][].

```shell
$ nosetests --immediate udata
```

You can launch a unique test too:

```shell
$ nosetests --immediate --stop --tests=udata/tests/api/test_datasets_api.py:DatasetResourceAPITest.test_reorder
```

If you want a fancy display, you can use the [nose-mocha-reporter][] (not installed by default) with the dedicated option:

```shell
$ nosetests --with-mocha-reporter --immediate --stop --tests=udata/tests/api/test_datasets_api.py:DatasetResourceAPITest
```

## Frontend unit tests

TODO

## Integration tests

We use [Watai][] which is using [webdriver API][] on top of [Selenium][].

First, install and launch Selenium:

```shell
$ selenium-server -p 4444
```

Then install watai and now you can run integration tests:

```shell
$ watai specs/integration/  --config '{"email":"name@example.org","password":"yourpassword","username":"yourusername"}'
```

You can easily exclude some tests if you want to run a particular range of test(s), here to run only test 4:

```shell
$ watai specs/integration/  --config '{"ignore":[1,2,3,5,6,7], "email":"name@example.org","password":"yourpassword","username":"yourusername"}'
```

Check out the [Watai tutorial][] to add your own tests!

[nosetest]: https://nose.readthedocs.org/en/latest/
[nose-mocha-reporter]: https://pypi.python.org/pypi/nose-mocha-reporter
[watai]: https://github.com/MattiSG/Watai
[webdriver api]: https://github.com/admc/wd/blob/master/doc/api.md
[selenium]: http://docs.seleniumhq.org/
[watai tutorial]: https://github.com/MattiSG/Watai/wiki/Tutorial
