from contextlib import contextmanager
from importlib import resources
from importlib.metadata import entry_points

import flask_babel
from flask import current_app, g, request
from flask_babel import Babel, refresh
from flask_login import current_user
from werkzeug.local import LocalProxy

from udata.app import Blueprint
from udata.errors import ConfigError


def get_translation_directories_and_domains():
    translations_dirs = []
    domains = []

    for pkg in entry_points(group="udata.i18n"):
        module = pkg.load()
        path = resources.files(module)
        # `/ ""` is  here to transform MultiplexedPath to a simple str
        translations_dirs.append(str(path / ""))
        domains.append(pkg.name)

    return translations_dirs, domains


def get_locale():
    if getattr(g, "lang_code", None):
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


def _default_lang(user=None):
    lang = getattr(user or current_user, "prefered_language", None)
    return lang or current_app.config["DEFAULT_LANGUAGE"]


default_lang = LocalProxy(lambda: _default_lang())


@contextmanager
def language(lang_code):
    """Force a given language"""
    ctx = None
    if not request:
        ctx = current_app.test_request_context()
        ctx.push()
    backup = g.get("lang_code")
    g.lang_code = lang_code
    refresh()
    yield
    g.lang_code = backup
    if ctx:
        ctx.pop()
    refresh()


def check_config(cfg):
    default_language = cfg["DEFAULT_LANGUAGE"]
    if default_language not in cfg.get("LANGUAGES", []):
        raise ConfigError(
            "You are using a DEFAULT_LANGUAGE {0} not defined into LANGUAGES".format(
                default_language
            )
        )


def init_app(app):
    check_config(app.config)
    translations_dir, domains = get_translation_directories_and_domains()
    Babel(
        app,
        default_locale=app.config["DEFAULT_LANGUAGE"],
        default_translation_directories=";".join(translations_dir),
        default_domain=";".join(domains),
        locale_selector=get_locale,
    )


class I18nBlueprint(Blueprint):
    pass
