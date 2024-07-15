from functools import wraps

from flask import current_app, request
from flask_sitemap import Sitemap, sitemap_page_needed

from udata.app import cache

sitemap = Sitemap()

CACHE_KEY = "sitemap-page-{0}"


@sitemap_page_needed.connect
def create_page(app, page, urlset):
    key = CACHE_KEY.format(page)
    cache.set(key, sitemap.render_page(urlset=urlset))


def load_page(fn):
    @wraps(fn)
    def loader(*args, **kwargs):
        page = kwargs.get("page")
        key = CACHE_KEY.format(page)
        return cache.get(key) or fn(*args, **kwargs)

    return loader


def set_scheme(fn):
    @wraps(fn)
    def set_scheme_on_call(*args, **kwargs):
        scheme = "https" if request.is_secure else "http"
        current_app.config["SITEMAP_URL_SCHEME"] = scheme
        return fn(*args, **kwargs)

    return set_scheme_on_call


def init_app(app):
    sitemap.decorators = []
    app.config["SITEMAP_VIEW_DECORATORS"] = [load_page, set_scheme]
    sitemap.init_app(app)
