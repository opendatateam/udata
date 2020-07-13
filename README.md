# udata-gouvfr

udata customizations for Etalab / Data.gouv.fr.

**Note:** This is a [udata][] extension, you should read the [udata documentation][udata-doc] first.

## Compatibility

**udata-gouvfr** requires Python 2.7+ and [uData][].


## Installation

Install [udata][].

Remain in the same Python virtual environment
and install **udata-gouvfr**:

```shell
pip install udata-gouvfr
```

Create a local configuration file `udata.cfg` in your **udata** directory
(or where your UDATA_SETTINGS point out) or modify an existing one as following:

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


[udata]: https://github.com/opendatateam/udata
[udata-doc]: http://udata.readthedocs.io/en/stable/
[udata-develop]: http://udata.readthedocs.io/en/stable/development-environment/
