from functools import wraps
from flask.ext.sitemap import Sitemap, sitemap_page_needed
from flask.ext.cache import Cache

from core.dataset.models import Dataset
from core.reuse.models import Reuse
from core.organization.models import Organization
from core.topic.models import Topic


def init_app(app):
    cache = Cache()
    sitemap = Sitemap()

    @sitemap_page_needed.connect
    def create_page(app, page, urlset):
        cache[page] = sitemap.render_page(urlset=urlset)

    def load_page(fn):
        @wraps(fn)
        def loader(*args, **kwargs):
            page = kwargs.get('page')
            try:
                data = cache.get(page)
            except KeyError:
                data = None
            return data if data else fn(*args, **kwargs)
        return loader

    @sitemap.register_generator
    def collect_urls():
        for item in Dataset.objects.visible():
            yield 'datasets.show_redirect', {'dataset': item.id}, None, "weekly", 1
        for item in Reuse.objects.visible():
            yield 'reuses.show_redirect', {'reuse': item}, None, "weekly", 0.8
        for item in Organization.objects.visible():
            yield 'organizations.show_redirect', {'org': item}, None, "weekly", 0.8
        for item in Topic.objects.all():
            yield 'topics.display_redirect', {'topic': item}, None, "weekly", 0.8

    app.config['SITEMAP_VIEW_DECORATORS'] = [load_page]
    sitemap.init_app(app)
