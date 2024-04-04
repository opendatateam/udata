import importlib.util

from contextlib import contextmanager
from os.path import join, dirname, basename
from glob import iglob

from flask import (  # noqa
    g, request, current_app, abort, redirect, url_for, has_request_context
)
from flask.blueprints import BlueprintSetupState, _endpoint_from_view_func

from babel.dates import format_timedelta as babel_format_timedelta

from datetime import datetime

import flask_babel
from flask_babel import Babel, refresh
from flask_babel import format_date, format_datetime  # noqa
from flask_babel import get_locale as get_current_locale  # noqa

from werkzeug.local import LocalProxy

from udata import entrypoints
from udata.app import Blueprint
from udata.auth import current_user
from udata.errors import ConfigError
from udata.utils import multi_to_dict


def get_translation_directories_and_domains():
    translations_dir = []
    domains = []

    # udata and plugin translations
    for pkg in entrypoints.get_roots(current_app):
        spec = importlib.util.find_spec(pkg)
        path = dirname(spec.origin)
        plugin_domains = [
            f.replace(path, '').replace('.pot', '')[1:]
            for f in iglob(join(path, '**/translations/*.pot'), recursive=True)]
        for domain in plugin_domains:
            translations_dir.append(join(path, dirname(domain)))
            domains.append(basename(domain))

    return translations_dir, domains


def get_locale():
    if getattr(g, 'lang_code', None):
        return g.lang_code
    return str(default_lang)


# Create shortcuts for the default Flask domain
def gettext(*args, **kwargs):
    return flask_babel.gettext(*args, **kwargs)


_ = gettext


def ngettext(*args, **kwargs):
    return flask_babel.ngettext(*args, **kwargs)


N_ = ngettext


def pgettext(*args, **kwargs):
    return flask_babel.pgettext(*args, **kwargs)


P_ = pgettext


def npgettext(*args, **kwargs):
    return flask_babel.npgettext(*args, **kwargs)


def lazy_gettext(*args, **kwargs):
    return flask_babel.lazy_gettext(*args, **kwargs)


L_ = lazy_gettext


def lazy_pgettext(*args, **kwargs):
    return flask_babel.lazy_pgettext(*args, **kwargs)


def format_timedelta(datetime_or_timedelta, granularity='second',
                     add_direction=False, threshold=0.85):
    '''This is format_timedelta from Flask-Babel'''
    '''Flask-BabelEx missed the add_direction parameter'''
    if isinstance(datetime_or_timedelta, datetime):
        datetime_or_timedelta = datetime.utcnow() - datetime_or_timedelta
    return babel_format_timedelta(datetime_or_timedelta,
                                  granularity,
                                  threshold=threshold,
                                  add_direction=add_direction,
                                  locale=get_current_locale())


def _default_lang(user=None):
    lang = getattr(user or current_user, 'prefered_language', None)
    return lang or current_app.config['DEFAULT_LANGUAGE']


default_lang = LocalProxy(lambda: _default_lang())


@contextmanager
def language(lang_code):
    '''Force a given language'''
    ctx = None
    if not request:
        ctx = current_app.test_request_context()
        ctx.push()
    backup = g.get('lang_code')
    g.lang_code = lang_code
    refresh()
    yield
    g.lang_code = backup
    if ctx:
        ctx.pop()
    refresh()


def check_config(cfg):
    default_language = cfg['DEFAULT_LANGUAGE']
    if default_language not in cfg.get('LANGUAGES', []):
        raise ConfigError('You are using a DEFAULT_LANGUAGE {0} not defined '
                          'into LANGUAGES'.format(default_language))


def init_app(app):
    check_config(app.config)
    translations_dir, domains = get_translation_directories_and_domains()
    Babel(
        app,
        default_locale=app.config['DEFAULT_LANGUAGE'],
        default_translation_directories=';'.join(translations_dir),
        default_domain=';'.join(domains),
        locale_selector=get_locale
    )


def _add_language_code(endpoint, values):
    try:
        if current_app.url_map.is_endpoint_expecting(endpoint, 'lang_code'):
            values.setdefault('lang_code', g.get('lang_code') or get_locale())
    except KeyError:  # Endpoint does not exist
        pass


def _pull_lang_code(endpoint, values):
    lang_code = values.pop('lang_code', g.get('lang_code') or get_locale())
    if lang_code not in current_app.config['LANGUAGES']:
        abort(redirect(
            url_for(endpoint, lang_code=default_lang, **values)))
    g.lang_code = lang_code


def redirect_to_lang(*args, **kwargs):
    '''Redirect non lang-prefixed urls to default language.'''
    endpoint = request.endpoint.replace('_redirect', '')
    kwargs = multi_to_dict(request.args)
    kwargs.update(request.view_args)
    kwargs['lang_code'] = default_lang
    return redirect(url_for(endpoint, **kwargs))


def redirect_to_unlocalized(*args, **kwargs):
    '''Redirect lang-prefixed urls to no prefixed URL.'''
    endpoint = request.endpoint.replace('_redirect', '')
    kwargs = multi_to_dict(request.args)
    kwargs.update(request.view_args)
    kwargs.pop('lang_code', None)
    return redirect(url_for(endpoint, **kwargs))


class I18nBlueprintSetupState(BlueprintSetupState):
    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """A helper method to register a rule (and optionally a view function)
        to the application.  The endpoint is automatically prefixed with the
        blueprint's name.
        The URL rule is registered twice.
        """
        # Static assets are not localized
        if endpoint == 'static':
            return super(I18nBlueprintSetupState, self).add_url_rule(
                rule, endpoint=endpoint, view_func=view_func, **options)
        if self.url_prefix:
            rule = self.url_prefix + rule
        options.setdefault('subdomain', self.subdomain)
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)
        defaults = self.url_defaults
        if 'defaults' in options:
            defaults = dict(defaults, **options.pop('defaults'))

        if options.pop('localize', True):
            self.app.add_url_rule('/<lang:lang_code>' + rule,
                                  '%s.%s' % (self.blueprint.name, endpoint),
                                  view_func, defaults=defaults, **options)

            self.app.add_url_rule(
                rule, '%s.%s_redirect' % (self.blueprint.name, endpoint),
                redirect_to_lang, defaults=defaults, **options)
        else:
            self.app.add_url_rule(rule,
                                  '%s.%s' % (self.blueprint.name, endpoint),
                                  view_func, defaults=defaults, **options)

            self.app.add_url_rule(
                '/<lang:lang_code>' + rule,
                '%s.%s_redirect' % (self.blueprint.name, endpoint),
                redirect_to_unlocalized, defaults=defaults, **options)


class I18nBlueprint(Blueprint):
    def make_setup_state(self, app, options, first_registration=False):
        return I18nBlueprintSetupState(self, app, options, first_registration)

    def register(self, *args, **kwargs):
        self.url_defaults(_add_language_code)
        self.url_value_preprocessor(_pull_lang_code)
        super(I18nBlueprint, self).register(*args, **kwargs)


ISO_639_1_CODES = (
    'aa', 'ab', 'af', 'am', 'an', 'ar', 'as', 'ay', 'az', 'ba', 'be', 'bg',
    'bh', 'bi', 'bn', 'bo', 'br', 'ca', 'co', 'cs', 'cy', 'da', 'de', 'dz',
    'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'fi', 'fj', 'fo', 'fr', 'fy',
    'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'hr', 'ht', 'hu',
    'hy', 'ia', 'id', 'ie', 'ii', 'ik', 'in', 'io', 'is', 'it', 'iu', 'iw',
    'ja', 'ji', 'jv', 'ka', 'kk', 'kl', 'km', 'kn', 'ko', 'ks', 'ku', 'ky',
    'la', 'li', 'ln', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml', 'mn', 'mo',
    'mr', 'ms', 'mt', 'my', 'na', 'ne', 'nl', 'no', 'oc', 'om', 'or', 'pa',
    'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sd', 'sg',
    'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su',
    'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr',
    'ts', 'tt', 'tw', 'ug', 'uk', 'ur', 'uz', 'vi', 'vo', 'wa', 'wo', 'xh',
    'yi', 'yo', 'zh', 'zh-Hans', 'zh-Hant', 'zu'
)
