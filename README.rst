=====
uData
=====

.. image:: https://secure.travis-ci.org/etalab/udata.png
    :target: http://travis-ci.org/etalab/udata
    :alt: Build status
.. image:: https://coveralls.io/repos/etalab/udata/badge.png?branch=master
    :target: https://coveralls.io/r/etalab/udata
    :alt: Code coverage
.. image:: https://requires.io/github/etalab/udata/requirements.png?branch=master
    :target: https://requires.io/github/etalab/udata/requirements/?branch=master
    :alt: Python Requirements Status
.. image:: https://www.versioneye.com/user/projects/5415870a9e1622cff80001cc/badge.svg?style=flat
    :target: https://www.versioneye.com/user/projects/5415870a9e1622cff80001cc/
    :alt: Javascript dependencies status

uData is an open and social data hub.
This currently a work in progress and API is subject to change until the first official release.

Compatibility
=============

udata requires Python 2.7+, MongoDB 2.6+, ElasticSearch 1.0+ and Redis.


Installation
============

You can install udata with pip:

.. code-block:: console

    $ pip install udata

or with easy_install:

.. code-block:: console

    $ easy_install udata

Then install npm dependencies with bower:

.. code-block:: console

    $ bower install

ElasticSearch
=============

The ICU plugin is required for ElasticSearch.

ICU Analysis: https://github.com/elasticsearch/elasticsearch-analysis-icu


Running
=======

To run the development server:

.. code-block:: console

    $ python manage.py serve

Your instance should be available at http://127.0.0.1:6666/


Documentation
=============

The documentation is hosted `on Read the Docs <http://udata.readthedocs.org/en/latest/>`_
