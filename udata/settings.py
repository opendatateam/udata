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
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "pt": "Português",
        "sr": "Српски",
        "de": "Deutsch",
    }
    DEFAULT_LANGUAGE = "en"
    SECRET_KEY = "Default uData secret key"
    CONTACT_EMAIL = "contact@example.org"
    TERRITORIES_EMAIL = "territories@example.org"

    MONGODB_HOST = "mongodb://localhost:27017/udata"
    MONGODB_CONNECT = False  # Lazy connexion for Fork-safe usage

    # Search service configuration
    SEARCH_SERVICE_API_URL = None
    SEARCH_SERVICE_REQUEST_TIMEOUT = 20

    # BROKER_TRANSPORT = 'redis'
    CELERY_BROKER_URL = "redis://localhost:6379"
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "fanout_prefix": True,
        "fanout_patterns": True,
    }
    CELERY_RESULT_BACKEND = "redis://localhost:6379"
    CELERY_RESULT_EXPIRES = 6 * HOUR  # Results are kept 6 hours
    CELERY_TASK_IGNORE_RESULT = True
    CELERY_TASK_SERIALIZER = "pickle"
    CELERY_RESULT_SERIALIZER = "pickle"
    CELERY_ACCEPT_CONTENT = ["pickle", "json"]
    CELERY_WORKER_HIJACK_ROOT_LOGGER = False
    CELERY_BEAT_SCHEDULER = "udata.tasks.Scheduler"
    CELERY_MONGODB_SCHEDULER_COLLECTION = "schedules"
    CELERY_MONGODB_SCHEDULER_CONNECTION_ALIAS = "udata_scheduler"

    # Default celery routing
    CELERY_TASK_DEFAULT_QUEUE = "default"
    CELERY_TASK_QUEUES = (
        # Default queue (on default exchange)
        Queue("default", routing_key="task.#"),
        # High priority for urgent tasks
        Queue("high", Exchange("high", type="topic"), routing_key="high.#"),
        # Low priority for slow tasks
        Queue("low", Exchange("low", type="topic"), routing_key="low.#"),
    )
    CELERY_TASK_DEFAULT_EXCHANGE = "default"
    CELERY_TASK_DEFAULT_EXCHANGE_TYPE = "topic"
    CELERY_TASK_DEFAULT_ROUTING_KEY = "task.default"
    CELERY_TASK_ROUTES = "udata.tasks.router"

    CACHE_KEY_PREFIX = "udata-cache"
    CACHE_TYPE = "flask_caching.backends.redis"

    # Flask mail settings

    MAIL_DEFAULT_SENDER = "webmaster@udata"

    # Flask security settings

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = None  # Can be set to 'Lax' or 'Strict'. See https://flask.palletsprojects.com/en/2.3.x/security/#security-cookie

    # Flask-Security-Too settings

    SECURITY_TRACKABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True

    SECURITY_PASSWORD_HASH = "bcrypt"
    SECURITY_PASSWORD_NORMALIZE_FORM = "NFKD"
    SECURITY_PASSWORD_LENGTH_MIN = 8
    SECURITY_PASSWORD_REQUIREMENTS_LOWERCASE = True
    SECURITY_PASSWORD_REQUIREMENTS_DIGITS = True
    SECURITY_PASSWORD_REQUIREMENTS_UPPERCASE = True
    SECURITY_PASSWORD_REQUIREMENTS_SYMBOLS = False

    SECURITY_PASSWORD_SALT = "Default uData secret password salt"
    SECURITY_CONFIRM_SALT = "Default uData secret confirm salt"
    SECURITY_RESET_SALT = "Default uData secret reset salt"
    SECURITY_REMEMBER_SALT = "Default uData remember salt"

    SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER

    SECURITY_EMAIL_SUBJECT_REGISTER = _("Welcome")
    SECURITY_EMAIL_SUBJECT_CONFIRM = _("Please confirm your email")
    SECURITY_EMAIL_SUBJECT_PASSWORDLESS = _("Login instructions")
    SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = _("Your password has been reset")
    SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE = _("Your password has been changed")
    SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = _("Password reset instructions")

    SECURITY_RETURN_GENERIC_RESPONSES = False

    # Sentry configuration
    SENTRY_DSN = None
    SENTRY_TAGS = {}
    SENTRY_USER_ATTRS = ["slug", "email", "fullname"]
    SENTRY_LOGGING = "WARNING"
    SENTRY_IGNORE_EXCEPTIONS = []
    SENTRY_SAMPLE_RATE: float = 1.0

    # Flask WTF settings
    CSRF_SESSION_KEY = "Default uData csrf key"

    # Flask-Sitemap settings
    # TODO: chose between explicit or automagic for params-less endpoints
    # SITEMAP_INCLUDE_RULES_WITHOUT_PARAMS = False
    SITEMAP_BLUEPRINT_URL_PREFIX = None

    AUTO_INDEX = True

    SITE_ID = "default"
    SITE_TITLE = "uData"
    SITE_KEYWORDS = ["opendata", "udata"]
    SITE_AUTHOR_URL = None
    SITE_AUTHOR = "Udata"
    SITE_GITHUB_URL = "https://github.com/etalab/udata"
    SITE_TERMS_LOCATION = pkg_resources.resource_filename(__name__, "terms.md")

    UDATA_INSTANCE_NAME = "udata"

    PLUGINS = []
    THEME = None

    STATIC_DIRS = []

    # OAuth 2 settings
    OAUTH2_PROVIDER_ERROR_ENDPOINT = "oauth.oauth_error"
    OAUTH2_REFRESH_TOKEN_GENERATOR = True
    OAUTH2_TOKEN_EXPIRES_IN = {
        "authorization_code": 30 * 24 * HOUR,
        "implicit": 10 * 24 * HOUR,
        "password": 30 * 24 * HOUR,
        "client_credentials": 30 * 24 * HOUR,
    }
    OAUTH2_ALLOW_WILDCARD_IN_REDIRECT_URI = False

    MD_ALLOWED_TAGS = [
        "a",
        "abbr",
        "acronym",
        "b",
        "br",
        "blockquote",
        "code",
        "dd",
        "del",
        "div",
        "dl",
        "dt",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "small",
        "span",
        "strong",
        "ul",
        "sup",
        "sub",
        "table",
        "td",
        "th",
        "tr",
        "tbody",
        "thead",
        "tfooter",
        "details",
        "summary",
        # 'title',
    ]

    MD_ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "rel", "data-tooltip"],
        "abbr": ["title"],
        "acronym": ["title"],
        "div": ["class"],
        "img": ["alt", "src", "title"],
    }

    MD_ALLOWED_STYLES = []

    # Extracted from https://github.github.com/gfm/#disallowed-raw-html-extension-
    MD_FILTERED_TAGS = [
        "title",
        "textarea",
        "style",
        "xmp",
        "iframe",
        "noembed",
        "noframes",
        "script",
        "plaintext",
    ]

    MD_ALLOWED_PROTOCOLS = ["http", "https", "ftp", "ftps"]

    # Tags constraints
    TAG_MIN_LENGTH = 3
    TAG_MAX_LENGTH = 96

    # Optionnal license groups used for a select input group widget
    # in admin dataset edit view.
    # A list of tuples, each tuple describing a group with its title and
    # a list of licenses associated. Translations are not supported.
    # Example:
    # LICENSE_GROUPS = [
    #     ("Autorités administratives", [
    #         {"value": "lov2", "recommended": True, "description": "Recommandée", "code": "etalab-2.0"},
    #         {"value": "notspecified", "description": "Le Code des relations entre le public et l’administration ne s’applique pas"}]),
    #     ("Tous producteurs", [
    #         {"value": "lov2", "recommended": True, "description": "Recommandée"},
    #         {"value": "cc-by", "code": "CC-BY"},
    #         {"value": "notspecified"}])
    # ]
    LICENSE_GROUPS = None

    # Cache duration for templates.
    TEMPLATE_CACHE_DURATION = 5  # Minutes.

    DELAY_BEFORE_REMINDER_NOTIFICATION = 30  # Days

    HARVEST_ENABLE_MANUAL_RUN = False

    HARVEST_PREVIEW_MAX_ITEMS = 20

    # Development setting to allow minimizing the number of harvested items
    HARVEST_MAX_ITEMS = None

    # Harvesters are scheduled at midnight by default
    HARVEST_DEFAULT_SCHEDULE = "0 0 * * *"

    # The number of days of harvest jobs to keep (ie. number of days of history kept)
    HARVEST_JOBS_RETENTION_DAYS = 365

    # The number of days since last harvesting date when a missing dataset is archived
    HARVEST_AUTOARCHIVE_GRACE_DAYS = 7

    HARVEST_VALIDATION_CONTACT_FORM = None

    HARVEST_MAX_CATALOG_SIZE_IN_MONGO = None  # Defaults to the size of a MongoDB document
    HARVEST_GRAPHS_S3_BUCKET = None  # If the catalog is bigger than `HARVEST_MAX_CATALOG_SIZE_IN_MONGO` store the graph inside S3 instead of MongoDB
    HARVEST_GRAPHS_S3_FILENAME_PREFIX = ""  # Useful to store the graphs inside a subfolder of the bucket. For example by setting `HARVEST_GRAPHS_S3_FILENAME_PREFIX = 'graphs/'`

    # S3 connection details
    S3_URL = None
    S3_ACCESS_KEY_ID = None
    S3_SECRET_ACCESS_KEY = None

    # Specific support for hvd (map HVD categories URIs to keywords)
    HVD_SUPPORT = True

    ACTIVATE_TERRITORIES = False
    # The order is important to compute parents/children, smaller first.
    HANDLED_LEVELS = tuple()

    LINKCHECKING_ENABLED = True
    # Resource types ignored by linkchecker
    LINKCHECKING_UNCHECKED_TYPES = ("api",)
    LINKCHECKING_IGNORE_DOMAINS = []
    LINKCHECKING_IGNORE_PATTERNS = ["format=shp"]
    LINKCHECKING_MIN_CACHE_DURATION = 60  # in minutes
    LINKCHECKING_MAX_CACHE_DURATION = 1080  # in minutes (1 week)
    LINKCHECKING_UNAVAILABLE_THRESHOLD = 100
    LINKCHECKING_DEFAULT_LINKCHECKER = "no_check"

    # Ignore some endpoint from API tracking
    # By default ignore the 3 most called APIs
    TRACKING_BLACKLIST = [
        "api.notifications",
        "api.check_dataset_resource",
        "api.avatar",
    ]

    DELETE_ME = True

    # Optimize uploaded images
    FS_IMAGES_OPTIMIZE = True

    # Default resources extensions whitelist

    ALLOWED_ARCHIVE_EXTENSIONS = [
        # Archives
        "tar",
        "gz",
        "tgz",
        "rar",
        "zip",
        "7z",
        "xz",
        "bz2",
    ]

    ALLOWED_RESOURCES_EXTENSIONS = ALLOWED_ARCHIVE_EXTENSIONS + [
        # Base
        "csv",
        "txt",
        "json",
        "pdf",
        "xml",
        "rtf",
        "xsd",
        # OpenOffice
        "ods",
        "odt",
        "odp",
        "odg",
        # Microsoft Office
        "xls",
        "xlsx",
        "doc",
        "docx",
        "pps",
        "ppt",
        # Images
        "jpeg",
        "jpg",
        "jpe",
        "gif",
        "png",
        "dwg",
        "svg",
        "tiff",
        "ecw",
        "svgz",
        "jp2",
        # Geo
        "shp",
        "kml",
        "kmz",
        "gpx",
        "shx",
        "ovr",
        "geojson",
        "gpkg",
        # Meteorology
        "grib2",
        # RDF
        "rdf",
        "ttl",
        "n3",
        # Misc
        "dbf",
        "prj",
        "sql",
        "sqlite",
        "db",
        "epub",
        "sbn",
        "sbx",
        "cpg",
        "lyr",
        "owl",
        "dxf",
        "ics",
        "ssim",
        "other",
    ]

    ALLOWED_RESOURCES_MIMES = [
        "text/csv",
        "application/json",
        "application/pdf",
        "application/msword",
        "application/vnd",
        "application/vnd.geo+json",
        "application/zip",
        "application/x-tar",
        "application/x-bzip",
        "application/x-bzip2",
        "application/x-7z-compressed",
        "application/x-rar-compressed",
        "application/epub+zip",
        "application/rtf",
        "application/rdf+xml",
        "application/xml",
        "application/xhtml+xml",
        "image/bmp",
        "image/jpeg",
        "image/png",
        "image/svg+xml",
        "text/html",
        "text/calendar",
        "text/plain",
        "text/xml",
        "text/turtle",
    ]

    # How much time upload chunks are kept before cleanup
    UPLOAD_MAX_RETENTION = 24 * HOUR

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

    # Organization settings
    ###########################################################################
    # The business identification format to use for validation
    ORG_BID_FORMAT = "siret"

    # Preview settings
    ###########################################################################
    # Preview mode can be either `iframe` or `page` or `None`
    PREVIEW_MODE = "iframe"

    # URLs validation settings
    ###########################################################################
    # Whether or not to allow private URLs (private IPs...) submission
    URLS_ALLOW_PRIVATE = False
    # Whether or not to allow local URLs (localhost...) submission.
    URLS_ALLOW_LOCAL = False
    # Whether or not to allow credentials in URLs submission.
    URLS_ALLOW_CREDENTIALS = True
    # List of allowed URL schemes.
    URLS_ALLOWED_SCHEMES = ("http", "https", "ftp", "ftps")
    # List of allowed TLDs.
    URLS_ALLOWED_TLDS = tld_set

    # Flask-CDN options
    # See: https://github.com/libwilliam/flask-cdn#flask-cdn-options
    # If this value is defined, toggle static assets on external domain
    CDN_DOMAIN = None
    # Don't check timestamp on assets (and avoid error on missing assets)
    CDN_TIMESTAMP = False

    # Export CSVs of model objects as resources of a dataset
    ########################################################
    EXPORT_CSV_MODELS = (
        "dataset",
        "resource",
        "discussion",
        "organization",
        "reuse",
        "tag",
        "harvest",
    )
    EXPORT_CSV_DATASET_ID = None

    # Autocomplete parameters
    #########################
    SEARCH_AUTOCOMPLETE_ENABLED = True
    SEARCH_AUTOCOMPLETE_DEBOUNCE = 200  # in ms

    # Archive parameters
    ####################
    ARCHIVE_COMMENT_USER_ID = None
    ARCHIVE_COMMENT_TITLE = _("This dataset has been archived")

    # Schemas parameters
    ####################
    SCHEMA_CATALOG_URL = None

    API_DOC_EXTERNAL_LINK = (
        "https://guides.data.gouv.fr/publier-des-donnees/guide-data.gouv.fr/api/reference"
    )

    # Read Only Mode
    ####################
    # This mode can be used to mitigate a spam attack for example.
    # It disables the methods listed in the following block list.
    READ_ONLY_MODE = False
    METHOD_BLOCKLIST = [
        "OrganizationListAPI.post",
        "ReuseListAPI.post",
        "DatasetListAPI.post",
        "CommunityResourcesAPI.post",
        "UploadNewCommunityResources.post",
        "DiscussionAPI.post",
        "DiscussionsAPI.post",
        "SourcesAPI.post",
        "FollowAPI.post",
    ]

    FIXTURE_DATASET_SLUGS = []
    PUBLISH_ON_RESOURCE_EVENTS = False
    RESOURCES_ANALYSER_URI = "http://localhost:8000"
    RESOURCES_ANALYSER_API_KEY = None

    # Datasets quality settings
    ###########################################################################
    QUALITY_DESCRIPTION_LENGTH = 100

    # Spam settings
    ###########################################################################
    SPAM_WORDS = []
    SPAM_ALLOWED_LANGS = []
    SPAM_MINIMUM_STRING_LENGTH_FOR_LANG_CHECK = 30

    # Notification settings
    ###########################################################################
    MATTERMOST_WEBHOOK = None


class Testing(object):
    """Sane values for testing. Should be applied as override"""

    TESTING = True
    # related to https://github.com/noirbizarre/flask-restplus/commit/93e412789f1ef8d1d2eab837f15535cf79bd144d#diff-68876137696247abc8c123622c73a11f  # noqa
    # this keeps our legacy tests from failing, we should probably fix the tests instead someday
    PROPAGATE_EXCEPTIONS = False
    SEND_MAIL = False
    WTF_CSRF_ENABLED = False
    AUTO_INDEX = False
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    TEST_WITH_PLUGINS = False
    PLUGINS = []
    TEST_WITH_THEME = False
    THEME = "testing"
    CACHE_TYPE = "flask_caching.backends.null"
    CACHE_NO_NULL_WARNING = True
    DEBUG_TOOLBAR = False
    SERVER_NAME = "local.test"
    DEFAULT_LANGUAGE = "fr"
    ACTIVATE_TERRITORIES = False
    LOGGER_HANDLER_POLICY = "never"
    CELERYD_HIJACK_ROOT_LOGGER = False
    URLS_ALLOW_LOCAL = True  # Test server URL is local.test
    URLS_ALLOWED_TLDS = tld_set | set(["test"])
    URLS_ALLOW_PRIVATE = False
    FS_IMAGES_OPTIMIZE = True
    SECURITY_EMAIL_VALIDATOR_ARGS = {
        "check_deliverability": False
    }  # Disables deliverability for email domain name
    PUBLISH_ON_RESOURCE_EVENTS = False


class Debug(Defaults):
    DEBUG = True
    SEND_MAIL = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PANELS = (
        "flask_debugtoolbar.panels.versions.VersionDebugPanel",
        "flask_debugtoolbar.panels.timer.TimerDebugPanel",
        "flask_debugtoolbar.panels.headers.HeaderDebugPanel",
        "flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel",
        "flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel",
        "flask_debugtoolbar.panels.template.TemplateDebugPanel",
        "flask_debugtoolbar.panels.logger.LoggingPanel",
        "flask_debugtoolbar.panels.profiler.ProfilerDebugPanel",
        "flask_mongoengine.panels.MongoDebugPanel",
    )
    CACHE_TYPE = "flask_caching.backends.null"
    CACHE_NO_NULL_WARNING = True
