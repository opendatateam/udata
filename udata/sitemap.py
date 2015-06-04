from __future__ import unicode_literals

from functools import wraps
from flask.ext.sitemap import Sitemap, sitemap_page_needed

from udata.app import cache


sitemap = Sitemap()


@sitemap_page_needed.connect
def create_page(app, page, urlset):
    cache.set(page, sitemap.render_page(urlset=urlset))


def load_page(fn):
    @wraps(fn)
    def loader(*args, **kwargs):
        page = kwargs.get('page')
        return cache.get(page) or fn(*args, **kwargs)
    return loader


def init_app(app):
    app.config['SITEMAP_VIEW_DECORATORS'] = [load_page]
    app.config['SITEMAP_URL_METHOD'] = 'https'
    sitemap.init_app(app)
