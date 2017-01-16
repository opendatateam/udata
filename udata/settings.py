# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class Defaults(object):
    DEBUG = False
    TESTING = False
    SEND_MAIL = True
    LANGUAGES = {
        'en': 'English',
        'fr': 'Français',
        'es': 'Español',
    }
    DEFAULT_LANGUAGE = 'en'
    SECRET_KEY = 'Default uData secret key'
    CONTACT_EMAIL = 'contact@example.org'
    TERRITORIES_EMAIL = 'territories@example.org'

    MONGODB_HOST = 'localhost'
    MONGODB_PORT = 27017
    MONGODB_DB = 'udata'

    # BROKER_TRANSPORT = 'redis'
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
    # CELERY_TASK_SERIALIZER = 'pickle'
    # CELERYD_POOL = 'gevent'

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
    SECURITY_PASSWORD_SALT = b'udata'

    SECURITY_PASSWORD_SALT = b'Default uData secret password salt'
    SECURITY_CONFIRM_SALT = b'Default uData secret confirm salt'
    SECURITY_RESET_SALT = b'Default uData secret reset salt'
    SECURITY_REMEMBER_SALT = b'Default uData remember salt'

    SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER

    # Flask WTF settings
    CSRF_SESSION_KEY = 'Default uData csrf key'

    OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 30 * 24 * 60 * 60  # 30 days

    AUTO_INDEX = True

    SITE_ID = 'default'
    SITE_TITLE = 'uData'
    SITE_KEYWORDS = ['opendata', 'udata']
    SITE_AUTHOR_URL = None
    SITE_AUTHOR = 'Udata'
    SITE_GITHUB_URL = 'https://github.com/etalab/udata'
    USE_SSL = False

    PLUGINS = []
    THEME = 'default'

    STATIC_DIRS = []

    OAUTH2_PROVIDER_ERROR_ENDPOINT = 'oauth-i18n.oauth_error'

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
    ]

    MD_ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
    }

    MD_ALLOWED_STYLES = []

    # Cache duration for templates.
    TEMPLATE_CACHE_DURATION = 5  # Minutes.

    DELAY_BEFORE_REMINDER_NOTIFICATION = 30  # Days

    HARVEST_PREVIEW_MAX_ITEMS = 20

    ACTIVATE_TERRITORIES = False
    # The order is important to compute parents/children, smaller first.
    HANDLED_LEVELS = tuple()

    # CROQUEMORT = {
    #     'url': 'http://localhost:8000',
    #     'delay': 1,
    #     'retry': 10,
    # }
    #
    CROQUEMORT_IGNORE = []

    # PIWIK_ID = # Demo = 11, Prod = 1
    # PIWIK_URL = 'stats.data.gouv.fr'
    # PIWIK_AUTH = '<32-chars-auth-token-from-piwik>'
    # # All keys are required.
    # PIWIK_GOALS = {
    #     'NEW_DATASET': # Demo = 1, Prod = 7
    #     'NEW_REUSE': # Demo = 2, Prod = 6
    #     'NEW_FOLLOW': # Demo = 3, Prod = 3
    #     'SHARE': , # Demo = 4, Prod = ?
    #     'RESOURCE_DOWNLOAD': , # Demo = 5, Prod = ?
    #     'RESOURCE_REDIRECT': , # Demo = 6, Prod = ?
    # }
    # TRACKING_BLACKLIST = ['api.notifications', 'api.checkurl']  # Default: []

    DELETE_ME = True


class Testing(object):
    '''Sane values for testing. Should be applied as override'''
    TESTING = True
    SEND_MAIL = False
    WTF_CSRF_ENABLED = False
    AUTO_INDEX = False
    CELERY_ALWAYS_EAGER = True
    TEST_WITH_PLUGINS = False
    PLUGINS = []
    TEST_WITH_THEME = False
    THEME = 'default'
    CACHE_TYPE = 'null'
    CACHE_NO_NULL_WARNING = True
    DEBUG_TOOLBAR = False
    SERVER_NAME = 'localhost'
    DEFAULT_LANGUAGE = 'en'
    ACTIVATE_TERRITORIES = False
    LOGGER_HANDLER_POLICY = 'never'
    CELERYD_HIJACK_ROOT_LOGGER = False


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
