from flask import current_app, g
from werkzeug.local import LocalProxy

from udata.core.dataset.models import Dataset
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.models import WithMetrics, db

__all__ = ("Site", "SiteSettings")


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

    __metrics_keys__ = [
        "max_dataset_followers",
        "max_dataset_reuses",
        "max_reuse_datasets",
        "max_reuse_followers",
        "max_org_followers",
        "max_org_reuses",
        "max_org_datasets",
        "datasets",
        "discussions",
        "followers",
        "organizations",
        "public-service",
        "resources",
        "reuses",
        "users",
        "harvesters",
    ]

    def __str__(self):
        return self.title or ""

    def count_users(self):
        from udata.models import User

        self.metrics["users"] = User.objects(confirmed_at__ne=None, deleted=None).count()
        self.save()

    def count_org(self):
        from udata.models import Organization

        self.metrics["organizations"] = Organization.objects.visible().count()
        self.save()

    def count_org_for_badge(self, badge_kind):
        from udata.models import Organization

        self.metrics[badge_kind] = Organization.objects(badges__kind=badge_kind).count()
        self.save()

    def count_datasets(self):
        from udata.models import Dataset

        self.metrics["datasets"] = Dataset.objects.visible().count()
        self.save()

    def count_resources(self):
        self.metrics["resources"] = next(
            Dataset.objects.visible().aggregate(
                {"$project": {"resources": 1}},
                {"$unwind": "$resources"},
                {"$group": {"_id": "result", "count": {"$sum": 1}}},
            ),
            {},
        ).get("count", 0)
        self.save()

    def count_reuses(self):
        self.metrics["reuses"] = Reuse.objects.visible().count()
        self.save()

    def count_followers(self):
        from udata.models import Follow

        self.metrics["followers"] = Follow.objects(until=None).count()
        self.save()

    def count_discussions(self):
        from udata.models import Discussion

        self.metrics["discussions"] = Discussion.objects.count()
        self.save()

    def count_harvesters(self):
        from udata.harvest.models import HarvestSource

        self.metrics["harvesters"] = HarvestSource.objects().count()
        self.save()

    def count_max_dataset_followers(self):
        dataset = (
            Dataset.objects(metrics__followers__gt=0)
            .visible()
            .order_by("-metrics.followers")
            .first()
        )
        self.metrics["max_dataset_followers"] = dataset.metrics["followers"] if dataset else 0
        self.save()

    def count_max_dataset_reuses(self):
        dataset = (
            Dataset.objects(metrics__reuses__gt=0).visible().order_by("-metrics.reuses").first()
        )
        self.metrics["max_dataset_reuses"] = dataset.metrics["reuses"] if dataset else 0
        self.save()

    def count_max_reuse_datasets(self):
        reuse = (
            Reuse.objects(metrics__datasets__gt=0).visible().order_by("-metrics.datasets").first()
        )
        self.metrics["max_reuse_datasets"] = reuse.metrics["datasets"] if reuse else 0
        self.save()

    def count_max_reuse_followers(self):
        reuse = (
            Reuse.objects(metrics__followers__gt=0).visible().order_by("-metrics.followers").first()
        )
        self.metrics["max_reuse_followers"] = reuse.metrics["followers"] if reuse else 0
        self.save()

    def count_max_org_followers(self):
        org = (
            Organization.objects(metrics__followers__gt=0)
            .visible()
            .order_by("-metrics.followers")
            .first()
        )
        self.metrics["max_org_followers"] = org.metrics["followers"] if org else 0
        self.save()

    def count_max_org_reuses(self):
        org = (
            Organization.objects(metrics__reuses__gt=0)
            .visible()
            .order_by("-metrics.reuses")
            .first()
        )
        self.metrics["max_org_reuses"] = org.metrics["reuses"] if org else 0
        self.save()

    def count_max_org_datasets(self):
        org = (
            Organization.objects(metrics__datasets__gt=0)
            .visible()
            .order_by("-metrics.datasets")
            .first()
        )
        self.metrics["max_org_datasets"] = org.metrics["datasets"] if org else 0
        self.save()


def get_current_site():
    if getattr(g, "site", None) is None:
        site_id = current_app.config["SITE_ID"]
        site_title = current_app.config.get("SITE_TITLE")
        site_keywords = current_app.config.get("SITE_KEYWORDS", [])
        g.site, _ = Site.objects.get_or_create(
            id=site_id,
            defaults={
                "title": site_title,
                "keywords": site_keywords,
            },
        )
        if g.site.title != site_title:
            Site.objects(id=site_id).modify(set__title=site_title)
        if g.site.keywords != site_keywords:
            Site.objects(id=site_id).modify(set__keywords=site_keywords)

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
