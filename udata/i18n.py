# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager
from importlib import import_module
from os.path import exists, join, dirname

from flask import g, request, current_app, abort, redirect, url_for
from flask.blueprints import BlueprintSetupState, _endpoint_from_view_func
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


from babel.support import NullTranslations, Translations

from flask.ext.babelex import Babel, Domain, refresh
from flask.ext.babelex import format_date, format_datetime
from flask.ext.babelex import get_locale as get_current_locale

from werkzeug.local import LocalProxy

from udata.app import Blueprint
from udata.auth import current_user
from udata.utils import multi_to_dict


class PluggableDomain(Domain):
    def get_translations(self):
        """Returns the correct gettext translations that should be used for
        this request.  This will never fail and return a dummy translation
        object if used outside of the request or if a translation cannot be
        found.
        """
        ctx = stack.top
        if ctx is None:
            return NullTranslations()

        locale = get_locale()

        cache = self.get_translations_cache(ctx)

        translations = cache.get(str(locale))
        if translations is None:
            translations_dir = self.get_translations_path(ctx)
            translations = Translations.load(translations_dir, locale, domain=self.domain)

            # Load plugins translations
            if isinstance(translations, Translations):
                # Load core extensions translations
                from wtforms.i18n import messages_path
                wtforms_translations = Translations.load(messages_path(), locale, domain='wtforms')
                translations.merge(wtforms_translations)

                for plugin_name in current_app.config['PLUGINS']:
                    module_name = 'udata.ext.{0}'.format(plugin_name)
                    module = import_module(module_name)
                    translations_dir = join(dirname(module.__file__), 'translations')
                    if exists(translations_dir):
                        domain = '-'.join((self.domain, plugin_name))
                        plugins_translations = Translations.load(translations_dir, locale, domain=domain)
                        translations.merge(plugins_translations)

                cache[str(locale)] = translations

        return translations


domain = PluggableDomain(domain='udata')
babel = Babel(default_domain=domain)


# Create shortcuts for the default Flask domain
def gettext(*args, **kwargs):
    return domain.gettext(*args, **kwargs)
_ = gettext


def ngettext(*args, **kwargs):
    return domain.ngettext(*args, **kwargs)
N_ = ngettext


def pgettext(*args, **kwargs):
    return domain.pgettext(*args, **kwargs)
P_ = pgettext


def npgettext(*args, **kwargs):
    return domain.npgettext(*args, **kwargs)


def lazy_gettext(*args, **kwargs):
    return domain.lazy_gettext(*args, **kwargs)


def lazy_pgettext(*args, **kwargs):
    return domain.lazy_pgettext(*args, **kwargs)


def _default_lang(user=None):
    user = user or current_user
    return user.prefered_language if user.is_authenticated() else current_app.config['DEFAULT_LANGUAGE']

default_lang = LocalProxy(lambda: _default_lang())


@contextmanager
def language(lang_code):
    backup = g.get('lang_code')
    g.lang_code = lang_code
    refresh()
    yield
    g.lang_code = backup
    refresh()


@babel.localeselector
def get_locale():
    if hasattr(g, 'lang_code'):
        return g.lang_code
    return default_lang


def init_app(app):
    app.config.setdefault('BABEL_DEFAULT_LOCALE', app.config['DEFAULT_LANGUAGE'])
    babel.init_app(app)


def _add_language_code(endpoint, values):
    if not endpoint.endswith('_redirect'):
        values.setdefault('lang_code', g.get('lang_code', default_lang))


def _pull_lang_code(endpoint, values):
    lang_code = values.pop('lang_code', g.get('lang_code', default_lang))
    if not lang_code in current_app.config['LANGUAGES']:
        try:
            abort(redirect(url_for(endpoint, lang_code=default_lang, **values)))
        except:
            abort(redirect(request.url.replace('/{0}/'.format(lang_code), '/{0}/'.format(default_lang))))
    g.lang_code = lang_code


def redirect_to_lang(*args, **kwargs):
    '''Redirect non lang-prefixed urls to default language.'''
    endpoint = request.endpoint.replace('_redirect', '')
    kwargs = multi_to_dict(request.args)
    kwargs.update(request.view_args)
    kwargs['lang_code'] = default_lang
    return redirect(url_for(endpoint, **kwargs))


class I18nBlueprintSetupState(BlueprintSetupState):
    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """A helper method to register a rule (and optionally a view function)
        to the application.  The endpoint is automatically prefixed with the
        blueprint's name.
        The URL rule is registered twice.
        """
        if self.url_prefix:
            rule = self.url_prefix + rule
        options.setdefault('subdomain', self.subdomain)
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)
        defaults = self.url_defaults
        if 'defaults' in options:
            defaults = dict(defaults, **options.pop('defaults'))
        self.app.add_url_rule('/<lang:lang_code>' + rule, '%s.%s' % (self.blueprint.name, endpoint),
                              view_func, defaults=defaults, **options)

        self.app.add_url_rule(rule, '%s.%s_redirect' % (self.blueprint.name, endpoint),
                              redirect_to_lang, defaults=defaults, **options)


class I18nBlueprint(Blueprint):
    def make_setup_state(self, app, options, first_registration=False):
        return I18nBlueprintSetupState(self, app, options, first_registration)

    def register(self, *args, **kwargs):
        self.url_defaults(_add_language_code)
        self.url_value_preprocessor(_pull_lang_code)
        super(I18nBlueprint, self).register(*args, **kwargs)
