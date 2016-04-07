# Testing your code

There a three complementary ways of testing your work: unit tests for the backend,
unit tests for the frontend and integration tests.

## Backend unit tests

The easiest way is to run Python tests with [nosetest][].

```shell
$ nosetests --immediate udata
```

You can launch a unique test too:

```shell
$ nosetests --immediate --stop --tests=udata/tests/api/test_datasets_api.py:DatasetResourceAPITest.test_reorder
```

If you want a fancy display, you can use the [nose-mocha-reporter][] (not installed by default)
with the dedicated option:

```shell
$ nosetests --with-mocha-reporter --immediate --stop --tests=udata/tests/api/test_datasets_api.py:DatasetResourceAPITest
```

## Frontend unit tests

For frontend (and administration) testing, we use the following tools:

* [Karma][] as test runner
* [mocha][] as test framework
* [Chai][] (and [some plugins][chai-plugins]) as assertions library
* [Sinon.JS][] for spies, stubs and mocks

All tests are located in the `specs` directory and should have the following naming pattern
`*.specs.js` to be recognized by Karma.

The most simple way to launch them is by using the dedicated invoke task:

```shell
$ inv jstest
```

It will run a single test pass using PhantomJS as browser.

You can continously run the test on any change detected by using the `--watch` option:

```shell
$ inv jstest --watch
```

For more advanced usage, you can use the npm dedicated run-scripts:

```shell
# Single run in PhantomJS
$ npm -s run test:unit
# Watch and run tests on change in PhantomJS
$ npm -s run test:watch
```

You can pass any option to karma after the `--`:

```bash
# Run tests a in new Chrome and Firefox instances
$ npm -s run test:unit -- --browsers Chrome,Firefox
# Single run with JUnit xml output
$ npm -s run test:unit -- --reporters mocha,junit
```

!!! note
    If using Chrome launcher without `chrome` being on the `$PATH` (or using Chromium),
    you need to specify the binary path by settings the environment variable
    `CHROME_BIN`

See [the official karma documentation][karma] for more details about the possible parameters.

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
[karma]: https://karma-runner.github.io/
[mocha]: https://mochajs.org/
[chai]: http://chaijs.com/
[chai-plugins]: http://chaijs.com/plugins/
[sinon.js]: http://sinonjs.org/
