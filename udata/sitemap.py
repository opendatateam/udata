from __future__ import unicode_literals

from functools import wraps
from flask_sitemap import Sitemap, sitemap_page_needed

from udata.app import cache


sitemap = Sitemap()

CACHE_KEY = 'sitemap-page-{0}'


@sitemap_page_needed.connect
def create_page(app, page, urlset):
    key = CACHE_KEY.format(page)
    cache.set(key, sitemap.render_page(urlset=urlset))


def load_page(fn):
    @wraps(fn)
    def loader(*args, **kwargs):
        page = kwargs.get('page')
        key = CACHE_KEY.format(page)
        return cache.get(key) or fn(*args, **kwargs)
    return loader


def init_app(app):
    sitemap.decorators = []
    app.config['SITEMAP_VIEW_DECORATORS'] = [load_page]
    app.config['SITEMAP_URL_METHOD'] = (
        'https' if app.config['USE_SSL'] else 'http')
    sitemap.init_app(app)
