# uData-gouvfr

[![Build status][circleci-badge]][circleci-url]
[![Join the chat at https://gitter.im/etalab/udata-gouvfr][gitter-badge]][gitter-url]

uData customizations for Etalab / Data.gouv.fr.

## Compatibility

**udata-gouvfr** requires Python 2.7+ and [uData][].


## Installation

Install [uData][].

Remain in the same virtual environment (for Python) and use the same version of npm (for JS).

Install **udata-gouvfr**:

```shell
git clone https://github.com/etalab/udata-gouvfr.git
pip install -e udata-gouvfr
```

Modify your local configuration file of **udata** (typically, `udata.cfg`) as following:

```python
PLUGINS = ['gouvfr']
THEME = 'gouvfr'
```

Build the assets:

```shell
inv assets
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
