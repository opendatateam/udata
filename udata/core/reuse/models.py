from blinker import Signal
from mongoengine.signals import post_save, pre_save
from werkzeug.utils import cached_property

from udata.api_fields import field, function_field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.dataset.api_fields import dataset_fields
from udata.core.owned import Owned, OwnedQuerySet
from udata.core.reuse.api_fields import BIGGEST_IMAGE_SIZE
from udata.core.storages import default_image_basename, images
from udata.frontend.markdown import mdstrip
from udata.i18n import lazy_gettext as _
from udata.mail import get_mail_campaign_dict
from udata.models import Badge, BadgeMixin, BadgesList, WithMetrics, db
from udata.mongo.errors import FieldValidationError
from udata.uris import endpoint_for
from udata.utils import hash_url

from .constants import IMAGE_MAX_SIZE, IMAGE_SIZES, REUSE_TOPICS, REUSE_TYPES

__all__ = ("Reuse",)

BADGES: dict[str, str] = {}


class ReuseQuerySet(OwnedQuerySet):
    def visible(self):
        return self(private__ne=True, datasets__0__exists=True, deleted=None)

    def hidden(self):
        return self(db.Q(private=True) | db.Q(datasets__0__exists=False) | db.Q(deleted__ne=None))


def check_url_does_not_exists(url, **_kwargs):
    """Ensure a reuse URL is not yet registered"""
    if url and Reuse.url_exists(url):
        raise FieldValidationError(_("This URL is already registered"), field="url")


def validate_badge(value):
    if value not in Reuse.__badges__.keys():
        raise db.ValidationError("Unknown badge type")


class ReuseBadge(Badge):
    kind = db.StringField(required=True, validation=validate_badge)


class ReuseBadgeMixin(BadgeMixin):
    badges = field(BadgesList(ReuseBadge), **BadgeMixin.default_badges_list_params)
    __badges__ = BADGES


@generate_fields(
    searchable=True,
    additional_sorts=[
        {"key": "datasets", "value": "metrics.datasets"},
        {"key": "followers", "value": "metrics.followers"},
        {"key": "views", "value": "metrics.views"},
    ],
    additional_filters={"organization_badge": "organization.badges"},
    mask="*,datasets{id,title,uri,page}",
)
class Reuse(db.Datetimed, Auditable, WithMetrics, ReuseBadgeMixin, Owned, db.Document):
    title = field(
        db.StringField(required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        db.SlugField(
            max_length=255, required=True, populate_from="title", update=True, follow=True
        ),
        readonly=True,
        auditable=False,
    )
    description = field(
        db.StringField(required=True),
        markdown=True,
    )
    type = field(
        db.StringField(required=True, choices=list(REUSE_TYPES)),
        filterable={},
    )
    url = field(
        db.URLField(required=True),
        description="The remote URL (website)",
        checks=[check_url_does_not_exists],
    )
    urlhash = db.StringField(required=True, unique=True)
    image_url = db.StringField()
    image = field(
        db.ImageField(
            fs=images,
            basename=default_image_basename,
            max_size=IMAGE_MAX_SIZE,
            thumbnails=IMAGE_SIZES,
        ),
        readonly=True,
        show_as_ref=True,
        thumbnail_info={
            "size": BIGGEST_IMAGE_SIZE,
        },
    )
    datasets = field(
        db.ListField(
            field(
                db.ReferenceField("Dataset", reverse_delete_rule=db.PULL),
                nested_fields=dataset_fields,
            ),
        ),
        filterable={
            "key": "dataset",
        },
    )
    tags = field(
        db.TagListField(),
        filterable={
            "key": "tag",
        },
    )
    topic = field(
        db.StringField(required=True, choices=list(REUSE_TOPICS)),
        filterable={},
    )
    # badges = db.ListField(db.EmbeddedDocumentField(ReuseBadge))

    private = field(db.BooleanField(default=False), filterable={})

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = field(db.ExtrasField(), auditable=False)

    featured = field(
        db.BooleanField(),
        filterable={},
        readonly=True,
        auditable=False,
    )
    deleted = field(
        db.DateTimeField(),
        auditable=False,
    )
    archived = field(
        db.DateTimeField(),
    )

    def __str__(self):
        return self.title or ""

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

    def url_for(self, *args, **kwargs):
        return endpoint_for("reuses.show", "api.reuse", reuse=self, *args, **kwargs)

    display_url = property(url_for)

    @function_field(description="Link to the API endpoint for this reuse", show_as_ref=True)
    def uri(self):
        return endpoint_for("api.reuse", reuse=self, _external=True)

    @function_field(description="Link to the udata web page for this reuse", show_as_ref=True)
    def page(self):
        return endpoint_for(
            "reuses.show", reuse=self, _external=True, fallback_endpoint="api.reuse"
        )

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
    def external_url_with_campaign(self):
        extras = get_mail_campaign_dict()
        return self.url_for(_external=True, **extras)

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
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_followers(self):
        from udata.models import Follow

        self.metrics["followers"] = Follow.objects(until=None).followers(self).count()
        self.save(signal_kwargs={"ignores": ["post_save"]})


pre_save.connect(Reuse.pre_save, sender=Reuse)
post_save.connect(Reuse.post_save, sender=Reuse)
