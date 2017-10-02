# uData-gouvfr

[![Build status][circleci-badge]][circleci-url]
[![Join the chat at https://gitter.im/etalab/udata-gouvfr][gitter-badge]][gitter-url]

uData customizations for Etalab / Data.gouv.fr.

**Note:** This is a [uData][] extension, you should read the [uData documentation][udata-doc] first.

## Compatibility

**udata-gouvfr** requires Python 2.7+ and [uData][].


## Installation

Install [uData][].

Remain in the same Python virtual environment
and install **udata-gouvfr**:

```shell
pip install udata-gouvfr
```

Modify your local configuration file of **udata** (typically, `udata.cfg`) as following:

```python
PLUGINS = ['gouvfr']
THEME = 'gouvfr'
```

## Development

Prepare a [udata development environment][udata-develop].

It is recommended to have a workspace with the following layout:

```shell
$WORKSPACE
├── fs
├── udata
│   ├── ...
│   └── setup.py
├── udata-gouvfr
│   ├── ...
│   └── setup.py
└── udata.cfg
```

The following steps use the same Python virtual environment
and the same version of npm (for JS) as `udata`.

Clone the `udata-gouvfr` repository into your workspace
and install it in development mode:

```shell
git clone https://github.com/etalab/udata-gouvfr.git
pip install -e udata-gouvfr
```

Modify your local `udata.cfg` configuration file as following:

```python
PLUGINS = ['gouvfr']
THEME = 'gouvfr'
```

You can execute `udata-gouvfr` specific tasks from the `udata-gouvfr` directory.

**ex:** Build the assets:

```shell
cd udata-gouvfr
npm install
inv assets-build
```

You can list available development commands with:

```shell
inv -l
```


[circleci-url]: https://circleci.com/gh/etalab/udata-gouvfr
[circleci-badge]: https://circleci.com/gh/etalab/udata-gouvfr.svg?style=shield
[gitter-badge]: https://badges.gitter.im/Join%20Chat.svg
[gitter-url]: https://gitter.im/etalab/udata-gouvfr
[uData]: https://github.com/opendatateam/udata
[udata-doc]: http://udata.readthedocs.io/en/stable/
[udata-develop]: http://udata.readthedocs.io/en/stable/development-environment/
