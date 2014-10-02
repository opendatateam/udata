# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class Defaults(object):
    DEBUG = False
    ASSETS_DEBUG = False
    TESTING = False
    LANGUAGES = {
        'en': 'English',
        'fr': 'Français',
        'es': 'Español',
    }
    DEFAULT_LANGUAGE = 'en'
    SECRET_KEY = 'Default uData secret key'
    MONGODB_SETTINGS = {'DB': 'udata'}

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

    SECURITY_PASSWORD_HASH = b'bcrypt'
    SECURITY_PASSWORD_SALT = b'udata'

    MAIL_DEFAULT_SENDER = 'webmaster@udata'

    AUTO_INDEX = True

    SITE_ID = 'default'
    SITE_TITLE = 'uData'
    SITE_KEYWORDS = ['opendata', 'udata']
    SITE_AUTHOR_URL = None
    SITE_AUTHOR = None
    USE_SSL = False

    PLUGINS = []
    THEME = 'default'

    OAUTH2_PROVIDER_ERROR_ENDPOINT = 'oauth-i18n.oauth_error'


class Testing(Defaults):
    TESTING = True
    MONGODB_SETTINGS = {'DB': 'udata-test'}
    WTF_CSRF_ENABLED = False
    AUTO_INDEX = False
    CELERY_ALWAYS_EAGER = True
    TEST_WITH_PLUGINS = False
    TEST_WITH_THEME = False
    ASSETS_AUTO_BUILD = False
    ASSETS_DEBUG = True


class Debug(Defaults):
    DEBUG = True
    ASSETS_DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PANELS = (
        'flask.ext.debugtoolbar.panels.versions.VersionDebugPanel',
        'flask.ext.debugtoolbar.panels.timer.TimerDebugPanel',
        'flask.ext.debugtoolbar.panels.headers.HeaderDebugPanel',
        'flask.ext.debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
        'flask.ext.debugtoolbar.panels.config_vars.ConfigVarsDebugPanel',
        'flask.ext.debugtoolbar.panels.template.TemplateDebugPanel',
        'flask.ext.debugtoolbar.panels.logger.LoggingPanel',
        'flask.ext.debugtoolbar.panels.profiler.ProfilerDebugPanel',
        'flask.ext.mongoengine.panels.MongoDebugPanel',
    )
    CACHE_TYPE = 'null'
    CACHE_NO_NULL_WARNING = True
