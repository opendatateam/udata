# Adapting settings

You can specify a configuration file by exporting the `UDATA_SETTINGS` environment variable.

```shell
export UDATA_SETTINGS=/path/to/my/udata.cfg
```

The configuration file is simply a Python file declaring variables.

udata uses a few Flask extensions and therefore provides all available options for these extensions.
Most of the time, it tries to provide sane defaults.

## Flask and global behavior options

### DEBUG

**default**: `False`

A boolean specifying the debug mode.

### SEND_MAIL

**default**: `True`

A boolean specifying if the emails should actually be sent.

### DEFAULT_LANGUAGE

**default**: `'en'`

The default fallback language when no language prefix is provided in URLs.

### SECRET_KEY

A secret key used as salt for cryptographic parts.
**You must specify your own secure key and use the same in all your instances**.

### SITE_ID

**default**: `'default'`

The site identifier. It is used to attached some database configuration, metrics...

### SITE_TERMS_LOCATION

**default**: `generic embedded terms`

The site terms in markdown. It can be either an URL or a local path to a markdown content.
If this is an URL, the content is downloaded on the first terms page display and cached.

### PLUGINS

**default**: `[]`

A list of enabled udata plugins.

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

### RESOURCES_FILE_ALLOWED_DOMAINS

**default**: `[]`

Whitelist of urls domains allowed for resources with `filetype` equals to `file`.

`SERVER_NAME` is always included.

`*` is a supported value as a wildcard allowing all domains.

### PREVIEW_MODE

**default**: `'iframe'`

Define the resources preview mode. Can be one of:
- `'iframe'`: preview are displayed into an iframe modal
- `'page'`: preview is displayed into a new page

If you want to disable preview, set `PREVIEW_MODE` to `None`

### ARCHIVE_COMMENT_USER_ID

**default**: `None`

The id of an existing user which will post a comment when a dataset is archived.

### ARCHIVE_COMMENT_TITLE

**default**: `_('This dataset has been archived')`

The title of the comment optionaly posted when a dataset is archived.
NB: the content of the comment is located in `udata/templates/comments/dataset_archived.txt`.


### SCHEMA_CATALOG_URL

**default** : `None`

The URL to a schema catalog, listing schemas resources can conform to. The URL should be a JSON endpoint, returning a schema catalog. Example: https://schema.data.gouv.fr/schemas/schemas.json

NB: this is used by the `datasets/schemas` API to fill the `schema` field of a `Resource`.

## URLs validation

### URLS_ALLOW_PRIVATE

**default**:  `False`

Whether or not to allow private URLs (private IPs...) submission

### URLS_ALLOW_LOCAL

**default**: `False`

Whether or not to allow local URLs (localhost...) submission.
When developping you might need to set this to `True`.

### URLS_ALLOW_CREDENTIALS

**default**: `True`

Whether or not to allow credentials in URLs submission.

### URLS_ALLOWED_SCHEMES

**default**: `('http', 'https', 'ftp', 'ftps')`

List of allowed URL schemes.

### URLS_ALLOWED_TLDS

**default**: All IANA registered TLDs

List of allowed TLDs.
When using udata on an intranet, you might want to add your own custom TLDs:

```python
from udata.settings import Defaults

URLS_ALLOWED_TLDS = Defaults.URLS_ALLOWED_TLDS + set(['custom', 'company'])
```

### EXPORT_CSV_MODELS

**default**: `('dataset', 'resource', 'discussion', 'organization', 'reuse', 'tag')`

List models that will be exported to CSV by the job `export-csv`.
You can disable the feature by setting this to an empty list.

### EXPORT_CSV_DATASET_ID

**default**: `None`

The id of a dataset that should be created before running the `export-csv` job and will hold the CSV exports.

## Search configuration

### SEARCH_AUTOCOMPLETE_ENABLED

**default**: `True`

Enables the search autocomplete on frontend if set to `True`, disables otherwise.

### SEARCH_AUTOCOMPLETE_DEBOUNCE

**default**: `200`

### SEARCH_SERVICE_API_URL

**default**: None

The independent search service api url to use if available.
If not specified, mongo full text search is used.

Ex:
```python
SEARCH_SERVICE_API_URL = 'http://127.0.0.1:5000/api/1/'
```

See [udata-search-service][udata-search-service] for more information on using a search service.

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

### HARVEST_MAX_ITEMS

**default**: `None`

The max number of items to fetch when harvesting (development setting)

### HARVEST_DEFAULT_SCHEDULE

**default**: `0 0 * * *`

A cron expression used as default harvester schedule when validating harvesters.

### HARVEST_JOBS_RETENTION_DAYS

**default**: `365`

The number of days of harvest jobs to keep (ie. number of days of history kept)

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

### LINKCHECKING_IGNORE_PATTERNS

**default**: ['format=shp']

A list patterns found in checked URL to ignore (ie `pattern in url`).

### LINKCHECKING_MIN_CACHE_DURATION

**default**: 60

The minimum time in minutes between two consecutive checks of a resource's url.

### LINKCHECKING_MAX_CACHE_DURATION

**default**: 1080

The maximum time in minutes between two consecutive checks of a resource's url.

### LINKCHECKING_UNAVAILABLE_THRESHOLD

**default**: 100

The number of unavailable checks after which the resource is considered lastingly unavailable and won't be checked as often.

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

An optional alternative mongo database used for testing.

## Celery options

By default, udata is configured to use Redis as Celery backend and a customized MongoDB scheduler.

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

**Note** Celery parameters changed in udata 1.2 because Celery has been upgraded to 4.1.0.
(You can get the change map [here][celery-conf-map]).
udata expect Celery parameters to be upper case and prefixed by `CELERY_` in your `udata.cfg`
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

## Authlib options

udata uses Authlib to provide OAuth2 on the API.
The full option list is available in
[the official Authlib documentation][authlib-doc]

### OAUTH2_TOKEN_EXPIRES_IN

**default**:
```python
    {
        'authorization_code': 10 * 24 * HOUR,
        'implicit': 10 * 24 * HOUR,
        'password': 10 * 24 * HOUR,
        'client_credentials': 10 * 24 * HOUR
    }
```

The OAuth2 token duration.

### OAUTH2_PROVIDER_ERROR_ENDPOINT

**default**: `'oauth.oauth_error'`

The OAuth2 error page. Do not modify unless you know what you are doing.

## Flask-Security options

### SECURITY_PASSWORD_LENGTH_MIN

**default**: `6`

The minimum required password length.

### SECURITY_PASSWORD_REQUIREMENTS_LOWERCASE

**default**: `False`

If set to `True`, the new passwords will need to contain at least one lowercase character.

### SECURITY_PASSWORD_REQUIREMENTS_DIGITS

**default**: `False`

If set to `True`, the new passwords will need to contain at least one digit.

### SECURITY_PASSWORD_REQUIREMENTS_UPPERCASE

**default**: `False`

If set to `True`, the new passwords will need to contain at least one uppercase character.

### SECURITY_PASSWORD_REQUIREMENTS_SYMBOLS

**default**: `False`

If set to `True`, the new passwords will need to contain at least one symbol.

## Inactive users deletion options

### YEARS_OF_INACTIVITY_BEFORE_DELETION

**default**: `None`

Set this setting to an int value to activate inactive users account notification and deletion.
It will filter on users with an account inactive for longer than this number of years.

#### DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY

**default**: 30

The delay of days between inactive user notification and its account deletion.

### MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS

**default**: 200

The maximal number of notifications to send per `notify-inactive-users` job.
If activating `YEARS_OF_INACTIVITY_BEFORE_DELETION`, you can slowly increase this configuration
batch after batch. The limitation is made to prevent sending too many mail notifications at once
resulting in your mail domain being flagged as spam.

## Flask-Cache options

udata uses Flask-Cache to handle cache and use Redis by default.
You can see the full options list in
[the official Flask-Cache documentation][flask-cache-doc]

### CACHE_TYPE

**default**: `'flask_caching.backends.redis'`

The cache type, which can be adjusted to your needs (_ex:_ `null`, `flask_caching.backends.memcached`)

### CACHE_KEY_PREFIX

**default**: `'udata-cache'`

A prefix used for cache keys to avoid conflicts with other middleware.
It also allows you to use the same backend with different instances.

## Flask-FS options

udata use Flask-FS as storage abstraction.

## Flask-CDN options

See [Flask-CDN README](https://github.com/libwilliam/flask-cdn#flask-cdn-options) for detailed options.

### CDN_DOMAIN

**default**: `None`

Set this to a domain name. If defined, udata will serve its static assets from this domain.

## Avatars/identicon configuration

Theses settings allow you to customize avatar rendering.
If defined to anything else than a falsy value, theses settings take precedence over the theme configuration and the default values.

### AVATAR_PROVIDER

**default** `'internal'`

Avatar provider used to render user avatars.

udata provides 3 backends:

- `internal`: udata renders avatars itself using [pydenticon](http://pydenticon.readthedocs.io)
- `adorable`: udata uses [Adorable Avatars](http://avatars.adorable.io/) to render avatars
- `robohash`: udata uses [Robohash](https://robohash.org/) to render avatars

### AVATAR_INTERNAL_SIZE

**default**: `7`

Number of blocks (the matrix size) used by the internal provider.

*E.g.*: `7` will render avatars on a 7x7 matrix

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

## Sentry configuration

### SENTRY_DSN

**default**: `None`

The Sentry DSN associated to this udata instance.
If defined, the Sentry support is automatically activated.

`sentry-sdk[flask]` needs to be installed for this to work. This requirement is specified in `requirements/sentry.pip`.

### SENTRY_TAGS

**default**: `{}`

A key-value map of extra tags to pass as Sentry context.
See: <https://docs.sentry.io/learn/context/>

### SENTRY_USER_ATTRS

**default**: `['slug', 'email', 'fullname']`

Extra user attributes to add the Sentry context.
See: <https://docs.sentry.io/learn/context/>

### SENTRY_LOGGING

**default**: `'WARNING'`

Minimum log level to be reported to Sentry.

### SENTRY_IGNORE_EXCEPTIONS

**default**: `[]`

A list of extra exceptions to ignore.
udata already ignores Werkzeug `HTTPException` and some internal ones
that don't need to be listed here.

## Read only mode

### READ_ONLY_MODE

**default**: `False`

Enables the app's read only mode.

### METHOD_BLOCKLIST

**default**: `['OrganizationListAPI.post', 'ReuseListAPI.post', 'DatasetListAPI.post', 'CommunityResourcesAPI.post', 'UploadNewCommunityResources.post', 'DiscussionAPI.post', 'DiscussionsAPI.post', 'IssuesAPI.post', 'IssueAPI.post', 'SourcesAPI.post', 'FollowAPI.post']`

List of API's endpoints to block when `READ_ONLY_MODE` is set to `True`. Endpoints listed here will return a `423` response code to any non-admin request.

## Fixtures

### FIXTURE_DATASET_SLUGS

**default**: `[]`

List of datasets slugs to query to fill the fixture file.

## Example configuration file

Here a sample configuration file:

```python
DEBUG = True
SEND_MAIL = False

SECRET_KEY = 'A unique secret key'

SERVER_NAME = 'www.data.dev'

DEFAULT_LANGUAGE = 'fr'
PLUGINS = ['front', 'piwik']
SITE_ID = 'www.data.dev'
SITE_TITLE = 'data.dev'
SITE_URL = 'www.data.dev'

DEBUG_TOOLBAR = True

FS_PREFIX = '/s'
FS_ROOT = '/srv/http/www.data.dev/fs'
```

[celery-doc]: http://docs.celeryproject.org/en/latest/userguide/configuration.html
[celery-conf-map]: http://docs.celeryproject.org/en/latest/userguide/configuration.html#conf-old-settings-map
[flask-cache-doc]: https://pythonhosted.org/Flask-Cache/
[flask-mail-doc]: https://flask-mail.readthedocs.io/
[flask-mongoengine-doc]: https://flask-mongoengine.readthedocs.org/
[authlib-doc]: https://docs.authlib.org/en/latest/flask/2/authorization-server.html#server
[udata-search-service]: https://github.com/opendatateam/udata-search-service

## Resources modifications publishing

udata may notify external services (ex: [hydra](https://github.com/datagouv/hydra)) about resources modification on the platform.
install, or any other service.


### PUBLISH_ON_RESOURCE_EVENTS

**default**: `False`

Publish resource events to an external service.

### RESOURCES_ANALYSER_URI

**default**: `http://localhost:8000`

URI of the external service receiving the resource events.

### RESOURCES_ANALYSER_API_KEY

**default**: `api_key_to_change`

API key sent in the headers of the endpoint requests as a Bearer token.
