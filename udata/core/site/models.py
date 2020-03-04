from flask import g, current_app
from werkzeug.local import LocalProxy
from werkzeug import cached_property

from udata.models import db, WithMetrics
from udata.core.organization.models import Organization
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
        return Reuse.objects.visible().count()

    @cached_property
    def folowers_count(self):
        from udata.models import Follow
        return Follow.objects(until=None).count()
    
    @property
    def discussion_count(self):
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
    
    @property
    def max_dataset_followers(self):
        # dataset = (Dataset.objects(metrics__followers__gt=0).visible()
        #                   .order_by('-metrics.followers').first())
        # return dataset.metrics['followers'] if dataset else 0
        return 0

    @property
    def max_dataset_reuses(self):
        # dataset = (Dataset.objects(metrics__reuses__gt=0).visible()
        #            .order_by('-metrics.reuses').first())
        # return dataset.metrics['reuses'] if dataset else 0
        return 0
    
    @property
    def max_reuse_datasets(self):
        # reuse = (Reuse.objects(metrics__datasets__gt=0).visible()
        #          .order_by('-metrics.datasets').first())
        # return reuse.metrics['datasets'] if reuse else 0
        return 0

    @property
    def max_reuse_followers(self):
        # reuse = (Reuse.objects(metrics__followers__gt=0).visible()
        #          .order_by('-metrics.followers').first())
        # return reuse.metrics['followers'] if reuse else 0
        return 0

    @property
    def max_org_followers(self):
        # org = (Organization.objects(metrics__followers__gt=0).visible()
        #        .order_by('-metrics.followers').first())
        # return org.metrics['followers'] if org else 0
        return 0

    @property
    def max_org_reuses(self):
        # org = (Organization.objects(metrics__reuses__gt=0).visible()
        #        .order_by('-metrics.reuses').first())
        # return org.metrics['reuses'] if org else 0
        return 0

    @property
    def max_org_datasets(self):
        # org = (Organization.objects(metrics__datasets__gt=0).visible()
        #        .order_by('-metrics.datasets').first())
        # return org.metrics['datasets'] if org else 0
        return 0


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
