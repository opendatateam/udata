============
uData-gouvfr
============

.. image:: https://secure.travis-ci.org/etalab/udata-gouvfr.png
    :target: http://travis-ci.org/etalab/udata-gouvfr
    :alt: Build status
.. image:: https://coveralls.io/repos/etalab/udata-gouvfr/badge.png?branch=master
    :target: https://coveralls.io/r/etalab/udata-gouvfr
    :alt: Code coverage

uData customizations for Etalab / Data.gouv.fr.

Compatibility
=============

**udata-gouvfr** requires Python 2.7+ and uData.


Installation
============

Install [udata](https://github.com/opendatateam/udata).

Remain in the same virtual environment (for Python) and use the same version of npm (for JS).

Install **udata-gouvfr**:

    git clone https://github.com/etalab/udata-gouvfr.git
    pip install -e udata-gouvfr

Modify the local configuration file of **udata** (typically, *udata.cfg*) as following:

    PLUGINS = ['gouvfr']
    THEME = 'gouvfr'

Build the assets:

    inv assets
