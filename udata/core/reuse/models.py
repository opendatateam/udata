from blinker import Signal
from mongoengine.signals import post_save, pre_save
from werkzeug.utils import cached_property

from udata.core.owned import Owned, OwnedQuerySet
from udata.core.storages import default_image_basename, images
from udata.frontend.markdown import mdstrip
from udata.i18n import lazy_gettext as _
from udata.models import BadgeMixin, WithMetrics, db
from udata.uris import endpoint_for
from udata.utils import hash_url

from .constants import IMAGE_MAX_SIZE, IMAGE_SIZES, REUSE_TOPICS, REUSE_TYPES

__all__ = ("Reuse",)


class ReuseQuerySet(OwnedQuerySet):
    def visible(self):
        return self(private__ne=True, datasets__0__exists=True, deleted=None)

    def hidden(self):
        return self(db.Q(private=True) | db.Q(datasets__0__exists=False) | db.Q(deleted__ne=None))


class Reuse(db.Datetimed, WithMetrics, BadgeMixin, Owned, db.Document):
    title = db.StringField(required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from="title", update=True, follow=True
    )
    description = db.StringField(required=True)
    type = db.StringField(required=True, choices=list(REUSE_TYPES))
    url = db.StringField(required=True)
    urlhash = db.StringField(required=True, unique=True)
    image_url = db.StringField()
    image = db.ImageField(
        fs=images, basename=default_image_basename, max_size=IMAGE_MAX_SIZE, thumbnails=IMAGE_SIZES
    )
    datasets = db.ListField(db.ReferenceField("Dataset", reverse_delete_rule=db.PULL))
    tags = db.TagListField()
    topic = db.StringField(required=True, choices=list(REUSE_TOPICS))
    # badges = db.ListField(db.EmbeddedDocumentField(ReuseBadge))

    private = db.BooleanField(default=False)

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.ExtrasField()

    featured = db.BooleanField()
    deleted = db.DateTimeField()
    archived = db.DateTimeField()

    def __str__(self):
        return self.title or ""

    __badges__ = {}

    __metrics_keys__ = [
        "discussions",
        "datasets",
        "followers",
        "views",
    ]

    meta = {
        "indexes": [
            "$title",
            "created_at",
            "last_modified",
            "metrics.datasets",
            "metrics.followers",
            "metrics.views",
            "urlhash",
        ]
        + Owned.meta["indexes"],
        "ordering": ["-created_at"],
        "queryset_class": ReuseQuerySet,
        "auto_create_index_on_save": True,
    }

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    verbose_name = _("reuse")

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        # Emit before_save
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        if "post_save" in kwargs.get("ignores", []):
            return
        cls.after_save.send(document)
        if kwargs.get("created"):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)
        if document.deleted:
            cls.on_delete.send(document)

    def url_for(self, *args, **kwargs):
        return endpoint_for("reuses.show", "api.reuse", reuse=self, *args, **kwargs)

    display_url = property(url_for)

    @property
    def is_visible(self):
        return not self.is_hidden

    @property
    def is_hidden(self):
        return len(self.datasets) == 0 or self.private or self.deleted

    @property
    def external_url(self):
        return self.url_for(_external=True)

    @property
    def type_label(self):
        return REUSE_TYPES[self.type]

    @property
    def topic_label(self):
        return REUSE_TOPICS[self.topic]

    def clean(self):
        super(Reuse, self).clean()
        """Auto populate urlhash from url"""
        if not self.urlhash or "url" in self._get_changed_fields():
            self.urlhash = hash_url(self.url)

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    @classmethod
    def url_exists(cls, url):
        urlhash = hash_url(url)
        return cls.objects(urlhash=urlhash).count() > 0

    @cached_property
    def json_ld(self):
        result = {
            "@context": "http://schema.org",
            "@type": "CreativeWork",
            "alternateName": self.slug,
            "dateCreated": self.created_at.isoformat(),
            "dateModified": self.last_modified.isoformat(),
            "url": endpoint_for("reuses.show", "api.reuse", reuse=self, _external=True),
            "name": self.title,
            "isBasedOnUrl": self.url,
        }

        if self.description:
            result["description"] = mdstrip(self.description)

        if self.organization:
            author = self.organization.json_ld
        elif self.owner:
            author = self.owner.json_ld
        else:
            author = None

        if author:
            result["author"] = author

        return result

    @property
    def views_count(self):
        return self.metrics.get("views", 0)

    def count_datasets(self):
        self.metrics["datasets"] = len(self.datasets)
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_discussions(self):
        from udata.models import Discussion

        self.metrics["discussions"] = Discussion.objects(subject=self, closed=None).count()
        self.save()

    def count_followers(self):
        from udata.models import Follow

        self.metrics["followers"] = Follow.objects(until=None).followers(self).count()
        self.save()


pre_save.connect(Reuse.pre_save, sender=Reuse)
post_save.connect(Reuse.post_save, sender=Reuse)
