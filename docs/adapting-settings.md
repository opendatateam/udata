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

## Spatial configuration

### SPATIAL_SEARCH_EXCLUDE_LEVELS

**default**: `tuple()`

List spatial levels that shoudn't be indexed (for time, performance and user experience).

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
HANDLED_LEVELS = ('fr:commune', 'fr:departement', 'fr:region')
```

## Harvesting configuration

### HARVEST_PREVIEW_MAX_ITEMS

**default**: `20`

The number of items to fetch while previewing an harvest source

### HARVEST_DEFAULT_SCHEDULE

**default**: `0 0 * * *`

A cron expression used as default harvester schedule when validating harvesters.

## Link checker configuration

### LINKCHECKING_ENABLED

**default**: `True`

A flag to enable the resources urls check by an external link checker.

### LINKCHECKING_DEFAULT_LINKCHECKER

**default**: `no_check`

An entrypoint key of `udata.linkcheckers` that will be used as a default link checker, i.e. when no specific link checker is set for a resource (via `resource.extras.check:checker`).

### LINKCHECKING_IGNORE_DOMAINS

**default**: []

A list of domains to ignore when triggering link checking of resources urls.

### LINKCHECKING_MIN_CACHE_DURATION

**default**: 60

The minimum time in minutes between two consecutive checks of a resource's url.

### LINKCHECKING_MAX_CACHE_DURATION

**default**: 1080

The maximum time in minutes between two consecutive checks of a resource's url.

### LINKCHECKING_UNAVAILABLE_THRESHOLD

**default**: 100

The number of unavailable checks after which the resource is considered lastingly unavailable and won't be checked as often.

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

### ELASTICSEARCH_URL_TEST

**default**: same as `ELASTICSEARCH_URL`

An optionnal alternative elasticsearch server url that may be used for testing.

### ELASTICSEARCH_INDEX_BASENAME

**default**: `'udata'`

The base name used to produce elasticsearch index names and alias.
The default `udata` value will produce:
- a `udata-{yyyy}-{mm}-{dd}-{HH}-{MM}` index on initialization
- a `udata` alias on `udata-{yyyy}-{mm}-{dd}-{HH}-{MM}` on initialization
- a temporary `udata-test` index during each test requiring it

```python
ELASTICSEARCH_INDEX_BASENAME = 'myindex'
```
The above example will produce:
- a `myindex-{yyyy}-{mm}-{dd}-{HH}-{MM}` index on initialization
- a `myindex` alias on `myindex-{yyyy}-{mm}-{dd}-{HH}-{MM}` on initialization
- a temporary `myindex-test` index during each test requiring it


## Mongoengine/Flask-Mongoengine options

### MONGODB_HOST

**default**: `'mongodb://localhost:27017/udata'`

The mongodb database used by udata.
During tests, the test database will use the same name suffixed by `-test`

See [the official Flask-MongoEngine documentation][flask-mongoengine-doc]
for more details.

Authentication is also supported in the URL:

```python
MONGODB_HOST = 'mongodb://<user>:<password>@<host>:<port>/<database>'
```

### MONGODB_HOST_TEST

**default**: same as `MONGODB_HOST` with a `-test` suffix on the collection

An optionnal alternative mongo database used for testing.

## Celery options

By default, uData is configured to use Redis as Celery backend and a customized MongoDB scheduler.

The defaults are:

```python
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'fanout_prefix': True,
    'fanout_patterns': True,
}
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_BEAT_SCHEDULER = 'udata.tasks.Scheduler'
CELERY_MONGODB_SCHEDULER_COLLECTION = "schedules"
```

Authentication is supported on Redis:

```python
CELERY_RESULT_BACKEND = 'redis://u:<password>@<host>:<port>'
CELERY_BROKER_URL = 'redis://u:<password>@<host>:<port>'
```

You can see the full list of Celery options in the [Celery official documentation][celery-doc].

**Note** Celery parameters changed in UData 1.2 because Celery has been upgraded to 4.1.0.
(You can get the change map [here][celery-conf-map]).
UData expect Celery parameters to be upper case and prefixed by `CELERY_` in your `udata.cfg`
and they will be automatically transformed for Celery 4.x:
Example:
 - Celery 3.x expected `BROKER_URL` and Celery 4.x expects `broker_url` so you need to change `BROKER_URL` to `CELERY_BROKER_URL` in your settings
 - Celery 3.X expected `CELERY_RESULT_BACKEND` and Celery 4.x expects `result_backend` so you can leave `CELERY_RESULT_BACKEND`

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

**default**: `'oauth.oauth_error'`

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

## Avatars/identicon configuration

Theses settings allow you to customize avatar rendering.
If defined to anything else than a falsy value, theses settings take precedence over the theme configuration and the default values.

### AVATAR_PROVIDER

**default** `'internal'`

Avatar provider used to render user avatars.

uData provides 3 backends:

- `internal`: uData renders avatars itself using [pydenticon](http://pydenticon.readthedocs.io)
- `adorable`: uData uses [Adorable Avatars](http://avatars.adorable.io/) to render avatars
- `robohash`: uData uses [Robohash](https://robohash.org/) to render avatars

### AVATAR_INTERNAL_SIZE

**default**: `7`

Number of blocks (the matrix size) used by the internal provider.

*Ex*: `7` will render avatars on a 7x7 matrix

### AVATAR_INTERNAL_FOREGROUND

**default**: `['rgb(45,79,255)', 'rgb(254,180,44)', 'rgb(226,121,234)', 'rgb(30,179,253)', 'rgb(232,77,65)', 'rgb(49,203,115)', 'rgb(141,69,170)']`

A list of foreground colors used by the internal provider to render the avatars

### AVATAR_INTERNAL_BACKGROUND

**default**: `'rgb(224,224,224)'`

The background color used by the internal provider

### AVATAR_INTERNAL_PADDING

**default**: `10`

The padding (in percent) used by the internal provider

### AVATAR_ROBOHASH_SKIN

**default**: `'set1'`

The skin (set) used by the robohash provider.
See <https://robohash.org/> for more details.

### AVATAR_ROBOHASH_BACKGROUND

**default**: `'bg0'` (transparent background)

The background used by the robohash provider.
See <https://robohash.org/> for more details.

## Posts configuration

Theses settings allow you to customize the post feature.

### POST_DISCUSSIONS_ENABLED

**default** `False`

Whether or not discussions should be enabled on posts

### POST_DEFAULT_PAGINATION

**default** `20`

The default page size for post listing

## Datasets configuration

### DATASET_MAX_RESOURCES_UNCOLLAPSED

**default** `6`

Max number of resources to display uncollapsed in dataset view.


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

[celery-doc]: http://docs.celeryproject.org/en/latest/userguide/configuration.html
[celery-conf-map]: http://docs.celeryproject.org/en/latest/userguide/configuration.html#conf-old-settings-map
[flask-cache-doc]: https://pythonhosted.org/Flask-Cache/
[flask-mail-doc]: https://pythonhosted.org/flask-mail/
[flask-mongoengine-doc]: https://flask-mongoengine.readthedocs.org/
[flask-oauthlib-doc]: https://flask-oauthlib.readthedocs.org/en/latest/oauth2.html#configuration
