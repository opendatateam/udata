# Adapting settings

You can specify a configuration file by exporting the `UDATA_SETTINGS` environment variable.

```shell
export UDATA_SETTINGS=/path/to/my/udata.cfg
```

The configuration file is simply a Python file declaring variables.

uData uses a few Flask extensions and therefore provides all available options for these extensions.
Most of the time, it tries to provide sane defaults.

## Flask and global behavior options

### DEBUG

**default**: `False`

A boolean specifying the debug mode.

### SEND_MAIL

**default**: `True`

A boolean specifying if the emails should actually be sent.

### USE_SSL

**default**: `False`

A boolean used to force SSL usage for logged in users.

### DEFAULT_LANGUAGE

**default**: `'en'`

The default fallback language when no language prefix is provided in URLs.

### SECRET_KEY

A secret key used as salt for cryptographic parts.
**You must specify your own secure key and use the same in all your instances**.

### SITE_ID

**default**: `'default'`

The site identifier. It is used to attached some database configuration, metrics...

### PLUGINS

**default**: `[]`

A list of enabled uData plugins.

### THEME

**default**: ``'default'``

The enabled theme name.

### TEMPLATE_CACHE_DURATION

**default**: `5`

The duration used for templates' cache, in minutes.

### ALLOWED_RESOURCES_EXTENSIONS

**default**:
```python
[
    # Base
    'csv', 'txt', 'json', 'pdf', 'xml', 'rdf', 'rtf', 'xsd',
    # OpenOffice
    'ods', 'odt', 'odp', 'odg',
    # Microsoft Office
    'xls', 'xlsx', 'doc', 'docx', 'pps', 'ppt',
    # Archives
    'tar', 'gz', 'tgz', 'rar', 'zip', '7z', 'xz', 'bz2',
    # Images
    'jpeg', 'jpg', 'jpe', 'gif', 'png', 'dwg', 'svg', 'tiff', 'ecw', 'svgz', 'jp2',
    # Geo
    'shp', 'kml', 'kmz', 'gpx', 'shx', 'ovr', 'geojson',
    # Meteorology
    'grib2',
    # Misc
    'dbf', 'prj', 'sql', 'epub', 'sbn', 'sbx', 'cpg', 'lyr', 'owl',
]
```

This is the allowed resources extensions list that user can upload.

## Territories configuration

### ACTIVATE_TERRITORIES

**default**: `False`

Whether you want to activate pages and API related to territories.
Don't forget to set the `HANDLED_LEVELS` setting too.

### HANDLED_LEVELS

**default**: `tuple()`

The list of levels that you want to deal with.

Warning: the order is important and will determine parents/children for
a given territory. You have to set the smallest territory level first:

```python
HANDLED_LEVELS = ('fr/town', 'fr/county', 'fr/region', 'country')
```

## ElasticSearch configuration

### ELASTICSEARCH_URL

**default**: `'localhost:9200'`

The elasticsearch server url used for search indexing.

```python
ELASTICSEARCH_URL = 'elasticserver:9200'
```

RFC-1738 formatted URLs are also supported:

```python
ELASTICSEARCH_URL = 'http://<user>:<password>@<host>:<port>'
```

## Mongoengine/Flask-Mongoengine options

### MONGODB_SETTINGS

**default**:
```python
MONGODB_SETTINGS = {
    'host': 'mongodb://localhost:27017/udata'
}
```

The mongodb database used by udata.
During tests, the test database will use the same name suffixed by `-test`

See [the official Flask-MongoEngine documentation][flask-mongoengine-doc]
for more details.

Authentication is also supported in the URL:

```python
MONGODB_SETTINGS = {
    'host': 'mongodb://<user>:<password>@<host>:<port>/<database>'
}
```

## Celery options

By default, uData is configured to use Redis as Celery backend and a customized MongoDB scheduler.

The defaults are:

```python
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
```

Authentication is supported on Redis:

```python
CELERY_RESULT_BACKEND = 'redis://u:<password>@<host>:<port>'
BROKER_URL = 'redis://u:<password>@<host>:<port>'
```

You can see the full list of Celery options in the [Celery official documentation][celery-doc].

## Flask-Mail options

You can see the full configuration option list in
[the official Flask-Mail documentation][flask-mail-doc].

### MAIL_DEFAULT_SENDER

**default**: `'webmaster@udata'`

The default identity used for outgoing mails.

## Flask-OAuthlib options

uData is Oauthlib to provide OAuth2 on the API.
The full option list is available in
[the official Flask-OAuthlib documentation][flask-oauthlib-doc]

### OAUTH2_PROVIDER_TOKEN_EXPIRES_IN

**default**: `30 * 24 * 60 * 60` (30 days)

The OAuth2 token duration.

### OAUTH2_PROVIDER_ERROR_ENDPOINT

**default**: `'oauth-i18n.oauth_error'`

The OAuth2 error page. Do not modify unless you know what you are doing.

## Flask-Cache options

uData uses Flask-Cache to handle cache and use Redis by default.
You can see the full options list in
[the official Flask-Cache documentation][flask-cache-doc]

### CACHE_TYPE

**default**: `'redis'`

The cache type, which can be adjusted to your needs (_ex:_ `null`, `memcached`)

### CACHE_KEY_PREFIX

**default**: `'udata-cache'`

A prefix used for cache keys to avoid conflicts with other middleware.
It also allows you to use the same backend with different instances.

### USE_METRICS

**default**: `True`

This activates metrics, this is deactivated for tests

## Flask-FS options

uData use Flask-FS as storage abstraction.

## Example configuration file

Here a sample configuration file:

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


DEBUG = True

SEND_MAIL = False

SECRET_KEY = 'A unique secret key'

USE_SSL = True
SERVER_NAME = 'www.data.dev'

DEFAULT_LANGUAGE = 'fr'
PLUGINS =  'gouvfr piwik youckan'.split()

SITE_ID = 'www.data.dev'
SITE_TITLE = 'Data.dev'
SITE_URL = 'www.data.dev'

DEBUG_TOOLBAR = True

FS_PREFIX = '/s'
FS_ROOT = '/srv/http/www.data.dev/fs'
```

[celery-doc]: https://docs.celeryproject.org/en/latest/configuration.html
[flask-cache-doc]: https://pythonhosted.org/Flask-Cache/
[flask-mail-doc]: https://pythonhosted.org/flask-mail/
[flask-mongoengine-doc]: https://flask-mongoengine.readthedocs.org/
[flask-oauthlib-doc]: https://flask-oauthlib.readthedocs.org/en/latest/oauth2.html#configuration
