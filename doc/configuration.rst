Configuration
=============

.. contents::
    :local:
    :depth: 2

You can specify a configuration file by exporting the
``UDATA_SETTINGS`` environment variable.

.. code-block:: shell

    export UDATA_SETTINGS=/path/to/my/udata.cfg


The configuration file is simply a Python file exporting some variables.


Example configuration file
--------------------------

Here a sample configuration file:

.. code-block:: python

    # -*- coding: utf-8 -*-
    from __future__ import unicode_literals


    DEBUG = True
    ASSETS_DEBUG = True
    ASSETS_AUTO_BUILD = True
    # REQUIREJS_RUN_IN_DEBUG = True

    SEND_MAIL = False

    SECRET_KEY = 'A unique secret key'

    USE_SSL = True
    SERVER_NAME = 'www.data.dev'

    DEFAULT_LANGUAGE = 'fr'
    PLUGINS =  'gouvfr piwik harvest me'.split()

    SITE_ID = 'www.data.dev'
    SITE_TITLE = 'Data.dev'
    SITE_URL = 'www.data.dev'

    DEBUG_TOOLBAR = True

    FS_PREFIX = '/s'
    FS_ROOT = '/srv/http/www.data.dev/fs'


Availables options
------------------

uData use some flask extensions and so provides all avaiable options for theses extensions.
Most of the time, it tries to provide some sane defaults.


Flask and global behavior options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DEBUG
*****

**default**: ``False``

A boolean specifying the debug mode.

SEND_MAIL
*********

**default**: ``True``

A boolean specifying if the emails should actually be sent.

USE_SSL
*******

**default**: ``False``

A boolean used to force SSL usage for logged in users.


DEFAULT_LANGUAGE
****************

**default**: ``'en'``

The default language used when no language prefix is provided in URLs.


SECRET_KEY
**********

A secret key used as salt for cryptographic parts.
**You must specify your own secure key and use same in all your instances**

SITE_ID
*******

**default**: ``'default'``

The site identifier. It is used to ataached some database configuration, metrics...


PLUGINS
*******

**default**: ``[]``

A list of enabled uData plugins.


THEME
*****

**default**: ``'default'``


The enabled theme name.


TEMPLATE_CACHE_DURATION
***********************

**default**: ``5``

The duration used for templates cache, in minutes.


Flask-Assets options
~~~~~~~~~~~~~~~~~~~~

ASSETS_DEBUG
************

**default**: ``False``

A boolean indicating whether assets should compiled or not allowing in-browser debugging.


ElasticSearch configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

ELASTICSEARCH_URL
*****************

**default**: ``'localhost:9200'``

The elasticsearch server url used for search indexing.

.. code-block:: python

    ELASTICSEARCH_URL = 'elasticserver:9200'


Mongoengine/Flask-Mongoengine options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MONGODB_HOST
************

**default**: ``localhost``

The mongodb hostname used by udata.


MONGODB_PORT
************

**default**: ``27017``

The mongodb post used by udata.

MONGODB_DB
**********

**default**: ``udata``

The mongodb database used by udata. When testing, the test database will use the same name suffixed by ``-test``


See `the official Flask-MongoEngine documentation <https://flask-mongoengine.readthedocs.org/en/latest/>`_ for more details.


Celery options
~~~~~~~~~~~~~~

By default, uData is configured to use Redis as Celery backend and a cutomized MongoDB scheduler.

The defaults are:

.. code-block:: python

    BROKER_URL = 'redis://localhost:6379'
    BROKER_TRANSPORT_OPTIONS = {
        'fanout_prefix': True,
        'fanout_patterns': True,
    }
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
    CELERY_ACCEPT_CONTENT = ['pickle', 'json']
    CELERYD_HIJACK_ROOT_LOGGER = False
    CELERYBEAT_SCHEDULER = 'udata.tasks.Scheduler'
    CELERY_MONGODB_SCHEDULER_COLLECTION = "schedules"

You can see the full list of Celery options in the
`Celery official documentation <http://docs.celeryproject.org/en/latest/configuration.html>`_.


Flask-Mail options
~~~~~~~~~~~~~~~~~~

You can see the full configuration option list in
`the official Flask-Mail documentation <https://pythonhosted.org/flask-mail/>`_

MAIL_DEFAULT_SENDER
*******************

**default**: ``'webmaster@udata'``

The default identity used for outgoing mails.


Flask-OAuthlib options
~~~~~~~~~~~~~~~~~~~~~~

uData is Oauthlib to provide OAuth2 on the API.
The full option list is available in
`the official Flask-OAuthlib documentation <https://flask-oauthlib.readthedocs.org/en/latest/oauth2.html#configuration>`_

OAUTH2_PROVIDER_TOKEN_EXPIRES_IN
********************************

**default**: ``30 * 24 * 60 * 60`` (30 days)

The OAuth2 token duration.


OAUTH2_PROVIDER_ERROR_ENDPOINT
******************************

**default**: ``'oauth-i18n.oauth_error'``

The OAuth2 error page. Do not modify unless you know what you do.


Flask-Cache options
~~~~~~~~~~~~~~~~~~~

uData use Flask-Cache to handle cache and use Redis by default.
You can see the full options list in
`the official Flask-Cache documentation <https://pythonhosted.org/Flask-Cache/>`_

CACHE_TYPE
**********

**default**: ``'redis'``

The cache type, which can be adjusted to your needs.


CACHE_KEY_PREFIX
****************

**default**: ``'udata-cache'``

A prefix used for cache keys to avoid conflict with other middleware.
It also allows you use the same backend with different instances.


Flask-FS options
~~~~~~~~~~~~~~~~

uData use Flask-FS as storage abstraction.
