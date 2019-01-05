# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pkg_resources

from kombu import Exchange, Queue
from tlds import tld_set

from udata.i18n import lazy_gettext as _


HOUR = 60 * 60


class Defaults(object):
    DEBUG = False
    TESTING = False
    SEND_MAIL = True
    LANGUAGES = {
        'en': 'English',
        'fr': 'Français',
        'es': 'Español',
        'pt': 'Português',
        'sr': 'Српски',
    }
    DEFAULT_LANGUAGE = 'en'
    SECRET_KEY = 'Default uData secret key'
    CONTACT_EMAIL = 'contact@example.org'
    TERRITORIES_EMAIL = 'territories@example.org'

    MONGODB_HOST = 'mongodb://localhost:27017/udata'
    MONGODB_CONNECT = False  # Lazy connexion for Fork-safe usage

    # Elasticsearch configuration
    ELASTICSEARCH_URL = 'localhost:9200'
    ELASTICSEARCH_INDEX_BASENAME = 'udata'
    ELASTICSEARCH_REFRESH_INTERVAL = '1s'

    # BROKER_TRANSPORT = 'redis'
    CELERY_BROKER_URL = 'redis://localhost:6379'
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'fanout_prefix': True,
        'fanout_patterns': True,
    }
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
    CELERY_RESULT_EXPIRES = 6 * HOUR  # Results are kept 6 hours
    CELERY_TASK_IGNORE_RESULT = True
    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_RESULT_SERIALIZER = 'pickle'
    CELERY_ACCEPT_CONTENT = ['pickle', 'json']
    CELERY_WORKER_HIJACK_ROOT_LOGGER = False
    CELERY_BEAT_SCHEDULER = 'udata.tasks.Scheduler'
    CELERY_MONGODB_SCHEDULER_COLLECTION = "schedules"

    # Default celery routing
    CELERY_TASK_DEFAULT_QUEUE = 'default'
    CELERY_TASK_QUEUES = (
        # Default queue (on default exchange)
        Queue('default', routing_key='task.#'),
        # High priority for urgent tasks
        Queue('high', Exchange('high', type='topic'), routing_key='high.#'),
        # Low priority for slow tasks
        Queue('low', Exchange('low', type='topic'), routing_key='low.#'),
    )
    CELERY_TASK_DEFAULT_EXCHANGE = 'default'
    CELERY_TASK_DEFAULT_EXCHANGE_TYPE = 'topic'
    CELERY_TASK_DEFAULT_ROUTING_KEY = 'task.default'
    CELERY_TASK_ROUTES = 'udata.tasks.router'

    CACHE_KEY_PREFIX = 'udata-cache'
    CACHE_TYPE = 'redis'

    # Flask mail settings

    MAIL_DEFAULT_SENDER = 'webmaster@udata'

    # Flask security settings

    SECURITY_TRACKABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True

    SECURITY_PASSWORD_HASH = b'bcrypt'

    SECURITY_PASSWORD_SALT = b'Default uData secret password salt'
    SECURITY_CONFIRM_SALT = b'Default uData secret confirm salt'
    SECURITY_RESET_SALT = b'Default uData secret reset salt'
    SECURITY_REMEMBER_SALT = b'Default uData remember salt'

    SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER

    SECURITY_EMAIL_SUBJECT_REGISTER = _('Welcome')
    SECURITY_EMAIL_SUBJECT_CONFIRM = _('Please confirm your email')
    SECURITY_EMAIL_SUBJECT_PASSWORDLESS = _('Login instructions')
    SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = _('Your password has been reset')
    SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE = _(
                                    'Your password has been changed')
    SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = _('Password reset instructions')

    # Sentry configuration
    SENTRY_DSN = None
    SENTRY_TAGS = {}
    SENTRY_USER_ATTRS = ['slug', 'email', 'fullname']
    SENTRY_LOGGING = 'WARNING'
    SENTRY_IGNORE_EXCEPTIONS = []

    # Flask WTF settings
    CSRF_SESSION_KEY = 'Default uData csrf key'

    # Flask-Sitemap settings
    # TODO: chose between explicit or automagic for params-less endpoints
    # SITEMAP_INCLUDE_RULES_WITHOUT_PARAMS = False
    SITEMAP_BLUEPRINT_URL_PREFIX = None

    AUTO_INDEX = True

    SITE_ID = 'default'
    SITE_TITLE = 'uData'
    SITE_KEYWORDS = ['opendata', 'udata']
    SITE_AUTHOR_URL = None
    SITE_AUTHOR = 'Udata'
    SITE_GITHUB_URL = 'https://github.com/etalab/udata'
    SITE_TERMS_LOCATION = pkg_resources.resource_filename(__name__, 'terms.md')

    PLUGINS = []
    THEME = 'default'

    STATIC_DIRS = []

    # OAuth 2 settings
    OAUTH2_PROVIDER_ERROR_ENDPOINT = 'oauth.oauth_error'
    OAUTH2_REFRESH_TOKEN_GENERATOR = True
    OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 30 * 24 * HOUR  # 30 days

    MD_ALLOWED_TAGS = [
        'a',
        'abbr',
        'acronym',
        'b',
        'br',
        'blockquote',
        'code',
        'dd',
        'dl',
        'dt',
        'em',
        'i',
        'li',
        'ol',
        'pre',
        'small',
        'strong',
        'ul',
        'sup',
        'sub',
    ]

    MD_ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
    }

    MD_ALLOWED_STYLES = []

    # Tags constraints
    TAG_MIN_LENGTH = 3
    TAG_MAX_LENGTH = 96

    # Cache duration for templates.
    TEMPLATE_CACHE_DURATION = 5  # Minutes.

    DELAY_BEFORE_REMINDER_NOTIFICATION = 30  # Days

    HARVEST_PREVIEW_MAX_ITEMS = 20
    # Harvesters are scheduled at midnight by default
    HARVEST_DEFAULT_SCHEDULE = '0 0 * * *'

    # Lists levels that shouldn't be indexed
    SPATIAL_SEARCH_EXCLUDE_LEVELS = tuple()

    ACTIVATE_TERRITORIES = False
    # The order is important to compute parents/children, smaller first.
    HANDLED_LEVELS = tuple()

    LINKCHECKING_ENABLED = True
    # Resource types ignored by linkchecker
    LINKCHECKING_UNCHECKED_TYPES = ('api', )
    LINKCHECKING_IGNORE_DOMAINS = []
    LINKCHECKING_MIN_CACHE_DURATION = 60  # in minutes
    LINKCHECKING_MAX_CACHE_DURATION = 1080  # in minutes (1 week)
    LINKCHECKING_UNAVAILABLE_THRESHOLD = 100
    LINKCHECKING_DEFAULT_LINKCHECKER = 'no_check'

    # Ignore some endpoint from API tracking
    # By default ignore the 3 most called APIs
    TRACKING_BLACKLIST = [
        'api.notifications',
        'api.check_dataset_resource',
        'api.avatar',
    ]

    DELETE_ME = True

    # Optimize uploaded images
    FS_IMAGES_OPTIMIZE = True

    # Default resources extensions whitelist
    ALLOWED_RESOURCES_EXTENSIONS = [
        # Base
        'csv', 'txt', 'json', 'pdf', 'xml', 'rtf', 'xsd',
        # OpenOffice
        'ods', 'odt', 'odp', 'odg',
        # Microsoft Office
        'xls', 'xlsx', 'doc', 'docx', 'pps', 'ppt',
        # Archives
        'tar', 'gz', 'tgz', 'rar', 'zip', '7z', 'xz', 'bz2',
        # Images
        'jpeg', 'jpg', 'jpe', 'gif', 'png', 'dwg', 'svg', 'tiff', 'ecw', 'svgz', 'jp2',
        # Geo
        'shp', 'kml', 'kmz', 'gpx', 'shx', 'ovr', 'geojson', 'gpkg',
        # Meteorology
        'grib2',
        # Misc
        'dbf', 'prj', 'sql', 'epub', 'sbn', 'sbx', 'cpg', 'lyr', 'owl',
        # RDF
        'rdf', 'ttl', 'n3',
    ]
    # Whitelist of urls domains for resource with filetype `file`
    # SERVER_NAME is always included, `*` is a supported value (wildcard)
    RESOURCES_FILE_ALLOWED_DOMAINS = []

    # How much time upload chunks are kept before cleanup
    UPLOAD_MAX_RETENTION = 24 * HOUR

    USE_METRICS = True

    # Avatar providers parameters
    # Overrides themes and default parameters
    # if set to anything else than `None`
    ###########################################################################
    # avatar provider used to render user avatars
    AVATAR_PROVIDER = None
    # Number of blocks used by the internal provider
    AVATAR_INTERNAL_SIZE = None
    # List of foreground colors used by the internal provider
    AVATAR_INTERNAL_FOREGROUND = None
    # Background color used by the internal provider
    AVATAR_INTERNAL_BACKGROUND = None
    # Padding (in percent) used by the internal provider
    AVATAR_INTERNAL_PADDING = None
    # Skin (set) used by the robohash provider
    AVATAR_ROBOHASH_SKIN = None
    # The background used by the robohash provider.
    AVATAR_ROBOHASH_BACKGROUND = None

    # Post settings
    ###########################################################################
    # Discussions on posts are disabled by default
    POST_DISCUSSIONS_ENABLED = False
    # Default pagination size on listing
    POST_DEFAULT_PAGINATION = 20

    # Dataset settings
    ###########################################################################
    # Max number of resources to display uncollapsed in dataset view
    DATASET_MAX_RESOURCES_UNCOLLAPSED = 6

    # Preview settings
    ###########################################################################
    # Preview mode can be either `iframe` or `page` or `None`
    PREVIEW_MODE = 'iframe'

    # URLs validation settings
    ###########################################################################
    # Whether or not to allow private URLs (private IPs...) submission
    URLS_ALLOW_PRIVATE = False
    # Whether or not to allow local URLs (localhost...) submission.
    URLS_ALLOW_LOCAL = False
    # Whether or not to allow credentials in URLs submission.
    URLS_ALLOW_CREDENTIALS = True
    # List of allowed URL schemes.
    URLS_ALLOWED_SCHEMES = ('http', 'https', 'ftp', 'ftps')
    # List of allowed TLDs.
    URLS_ALLOWED_TLDS = tld_set

    # Map/Tiles configuration
    ###########################################################################
    # Tiles URL for SD displays
    MAP_TILES_URL = 'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png'
    # Tiles URL for HD/HiDPI displays
    MAP_TILES_URL_HIDPI = 'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}@2x.png'
    # Leaflet tiles config, see https://leafletjs.com/reference-0.7.7.html#tilelayer
    MAP_TILES_CONFIG = {
        'subdomains': 'abcd',
        'attribution': (
            '&copy;'
            '<a href="http://openstreetmap.org/copyright">OpenStreetMap</a>'
            '/'
            '<a href="https://cartodb.com/attributions">CartoDB</a>'
        )
    }
    # Initial map center position
    MAP_INITIAL_CENTER = [42, 2.4]
    # Initial map zoom level
    MAP_INITIAL_ZOOM = 4
    # Initial map territory level
    MAP_INITIAL_LEVEL = 0
    # Flask-CDN options
    # See: https://github.com/libwilliam/flask-cdn#flask-cdn-options
    # If this value is defined, toggle static assets on external domain
    CDN_DOMAIN = None
    # Don't check timestamp on assets (and avoid error on missing assets)
    CDN_TIMESTAMP = False

    # Export CSVs of model objects as resources of a dataset
    ########################################################
    # which models should be exported
    EXPORT_CSV_MODELS = ('dataset', 'resource', 'discussion', 'organization',
                         'reuse', 'tag')
    EXPORT_CSV_DATASET_INFO = {
        'slug': 'export-csv',
        'title': 'Export of portal data',
        'description': 'This dataset holds the CSV exports of this portal\'s data.',
        # this should point to an existing organization id
        'organization': None,
    }


class Testing(object):
    '''Sane values for testing. Should be applied as override'''
    TESTING = True
    SEND_MAIL = False
    WTF_CSRF_ENABLED = False
    AUTO_INDEX = False
    CELERY_TASK_ALWAYS_EAGER = True
    TEST_WITH_PLUGINS = False
    PLUGINS = []
    TEST_WITH_THEME = False
    THEME = 'default'
    CACHE_TYPE = 'null'
    CACHE_NO_NULL_WARNING = True
    DEBUG_TOOLBAR = False
    SERVER_NAME = 'local.test'
    DEFAULT_LANGUAGE = 'en'
    ACTIVATE_TERRITORIES = False
    LOGGER_HANDLER_POLICY = 'never'
    CELERYD_HIJACK_ROOT_LOGGER = False
    USE_METRICS = False
    RESOURCES_FILE_ALLOWED_DOMAINS = ['*']
    URLS_ALLOW_LOCAL = True  # Test server URL is local.test
    URLS_ALLOWED_TLDS = tld_set | set(['test'])
    URLS_ALLOW_PRIVATE = False


class Debug(Defaults):
    DEBUG = True
    SEND_MAIL = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PANELS = (
        'flask_debugtoolbar.panels.versions.VersionDebugPanel',
        'flask_debugtoolbar.panels.timer.TimerDebugPanel',
        'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
        'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
        'flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel',
        'flask_debugtoolbar.panels.template.TemplateDebugPanel',
        'flask_debugtoolbar.panels.logger.LoggingPanel',
        'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
        'flask_mongoengine.panels.MongoDebugPanel',
    )
    CACHE_TYPE = 'null'
    CACHE_NO_NULL_WARNING = True
