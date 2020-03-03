from flask import g, current_app
from werkzeug.local import LocalProxy
from werkzeug import cached_property

from udata.models import db, WithMetrics
from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse


__all__ = ('Site', 'SiteSettings')


DEFAULT_FEED_SIZE = 20


class SiteSettings(db.EmbeddedDocument):
    home_datasets = db.ListField(db.ReferenceField(Dataset))
    home_reuses = db.ListField(db.ReferenceField(Reuse))


class Site(WithMetrics, db.Document):
    id = db.StringField(primary_key=True)
    title = db.StringField(required=True)
    keywords = db.ListField(db.StringField())
    feed_size = db.IntField(required=True, default=DEFAULT_FEED_SIZE)
    configs = db.DictField()
    themes = db.DictField()
    settings = db.EmbeddedDocumentField(SiteSettings, default=SiteSettings)

    def __str__(self):
        return self.title or ''
    
    @cached_property
    def users_count(self):
        from udata.models import User
        return User.objects.count()
    
    @cached_property
    def org_count(self):
        from udata.models import Organization
        return Organization.objects.visible().count()

    @cached_property
    def datasets_count(self):
        from udata.models import Dataset
        return Dataset.objects.visible().count()
    
    @cached_property
    def resources_count(self):
        return next(Dataset.objects.visible().aggregate(
            {'$project': {'resources': 1}},
            {'$unwind': '$resources' },
            {'$group': {'_id': 'result', 'count': {'$sum': 1}}}
        ), {}).get('count', 0)

    @cached_property
    def reuses_count(self):
        from udata.models import Reuse
        return Reuse.objects.visible().count()

    @cached_property
    def folowers_count(self):
        from udata.models import Follow
        return Follow.objects(until=None).count()
    
    @cached_property
    def dicussion_count(self):
        from udata.models import Discussion
        return Discussion.objects.count()
    
    @property
    def get_metrics(self):
        return {
            "datasets": 34556,
            "discussions": 5329,
            "followers": 21757,
            "organizations": 2514,
            "public_services": 462,
            "resources": 187202,
            "reuses": 2032,
            "users": 50458
        }


def get_current_site():
    if getattr(g, 'site', None) is None:
        site_id = current_app.config['SITE_ID']
        g.site, _ = Site.objects.get_or_create(id=site_id, defaults={
            'title': current_app.config.get('SITE_TITLE'),
            'keywords': current_app.config.get('SITE_KEYWORDS', []),
        })
    return g.site


current_site = LocalProxy(get_current_site)


@Dataset.on_delete.connect
def remove_from_home_datasets(dataset):
    if dataset in current_site.settings.home_datasets:
        current_site.settings.home_datasets.remove(dataset)
        current_site.save()


@Reuse.on_delete.connect
def remove_from_home_reuses(reuse):
    if reuse in current_site.settings.home_reuses:
        current_site.settings.home_reuses.remove(reuse)
        current_site.save()
