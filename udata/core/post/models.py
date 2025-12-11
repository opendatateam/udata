from flask import url_for

from udata.api_fields import field, generate_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.linkable import Linkable
from udata.core.storages import default_image_basename, images
from udata.i18n import lazy_gettext as _
from udata.mongo import db
from udata.uris import cdata_url

from .constants import BODY_TYPES, IMAGE_SIZES

__all__ = ("Post",)


class PostQuerySet(db.BaseQuerySet):
    def published(self):
        return self(published__ne=None).order_by("-published")


@generate_fields(
    searchable=True,
    additional_sorts=[
        {"key": "created_at", "value": "created_at"},
        {"key": "modified", "value": "last_modified"},
    ],
    default_sort="-published",
)
class Post(db.Datetimed, Linkable, db.Document):
    name = field(
        db.StringField(max_length=255, required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        readonly=True,
    )
    headline = field(
        db.StringField(),
        sortable=True,
    )
    content = field(
        db.StringField(required=True),
        markdown=True,
    )
    image_url = field(
        db.StringField(),
    )
    image = field(
        db.ImageField(fs=images, basename=default_image_basename, thumbnails=IMAGE_SIZES),
        readonly=True,
        thumbnail_info={"size": 100},
    )

    credit_to = field(
        db.StringField(),
        description="An optional credit line (associated to the image)",
    )
    credit_url = field(
        db.URLField(),
        description="An optional link associated to the credits",
    )

    tags = field(
        db.ListField(db.StringField()),
        description="Some keywords to help in search",
    )
    datasets = field(
        db.ListField(
            field(
                db.ReferenceField("Dataset", reverse_delete_rule=db.PULL),
                nested_fields=dataset_fields,
            )
        ),
        description="The post datasets",
    )
    reuses = field(
        db.ListField(db.ReferenceField("Reuse", reverse_delete_rule=db.PULL)),
        description="The post reuses",
    )

    owner = field(
        db.ReferenceField("User"),
        readonly=True,
        allow_null=True,
        description="The owner user",
    )
    published = field(
        db.DateTimeField(),
        readonly=True,
        sortable=True,
        description="The post publication date",
    )

    body_type = field(
        db.StringField(choices=list(BODY_TYPES), default="markdown", required=False),
        description="HTML or markdown body type",
    )

    meta = {
        "ordering": ["-created_at"],
        "indexes": [
            "-created_at",
            "-published",
            {
                "fields": ["$name", "$headline", "$content"],
                "default_language": "french",
                "weights": {"name": 10, "headline": 5, "content": 4},
            },
        ],
        "queryset_class": PostQuerySet,
    }

    verbose_name = _("post")

    def __str__(self):
        return self.name or ""

    def self_web_url(self, **kwargs):
        return cdata_url(f"/posts/{self._link_id(**kwargs)}", **kwargs)

    def self_api_url(self, **kwargs):
        return url_for(
            "api.post", post=self._link_id(**kwargs), **self._self_api_url_kwargs(**kwargs)
        )

    @field(description="The API URI for this post")
    def uri(self):
        return self.self_api_url()

    @field(description="The post web page URL")
    def page(self):
        return self.self_web_url()

    def count_discussions(self):
        # There are no metrics on Post to store discussions count
        pass
