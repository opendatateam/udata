# uData

[![Dependencies Status][david-image]][david-url] [![Dev Dependencies Status][david-dev-image]][david-dev-url]

uData is an open and social data hub.
This currently a work in progress and API is subject to change until the first official release.

## Running tests

Continuously run the Mocha tests:

    $ inv jstest

## Documentation

The documentation is hosted [on Read the Docs][readthedoc]

## Translations

Extract string from templates and code:

    $ inv i18n && tx push -s

Fetch last translations:

    $ tx pull -f && inv i18nc

You have to set a [`~/.transifexrc`][transifexrc] first.

[david-url]: https://david-dm.org/etalab/udata
[david-image]: https://img.shields.io/david/etalab/udata.svg
[david-dev-url]: https://david-dm.org/etalab/udata#info=devDependencies
[david-dev-image]: https://david-dm.org/etalab/udata/dev-status.svg
[readthedoc]: http://udata.readthedocs.org/en/latest/
[transifexrc]: http://docs.transifex.com/client/config/
