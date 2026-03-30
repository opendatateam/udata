from flask import url_for
from flask_storage.mongo import ImageField
from mongoengine import PULL
from mongoengine.errors import ValidationError
from mongoengine.fields import (
    DateTimeField,
    EmbeddedDocumentListField,
    ListField,
    ReferenceField,
    StringField,
)

from udata.api_fields import field, generate_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.edito_blocs.models import Bloc
from udata.core.linkable import Linkable
from udata.core.storages import default_image_basename, images
from udata.core.user.api_fields import user_ref_fields
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.queryset import UDataQuerySet
from udata.mongo.slug_fields import SlugField
from udata.mongo.url_field import URLField
from udata.uris import cdata_url

from .constants import BODY_TYPES, IMAGE_SIZES, POST_KINDS

__all__ = ("Post",)


class PostQuerySet(UDataQuerySet):
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
class Post(Datetimed, Linkable, Document[PostQuerySet]):
    name = field(
        StringField(max_length=255, required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        readonly=True,
    )
    headline = field(
        StringField(),
        sortable=True,
    )
    content = field(
        StringField(),
        markdown=True,
    )
    blocs = field(
        EmbeddedDocumentListField(Bloc),
        generic=True,
    )
    image_url = field(
        StringField(),
    )
    image = field(
        ImageField(fs=images, basename=default_image_basename, thumbnails=IMAGE_SIZES),
        readonly=True,
        thumbnail_info={"size": 100},
    )

    credit_to = field(
        StringField(),
        description="An optional credit line (associated to the image)",
    )
    credit_url = field(
        URLField(),
        description="An optional link associated to the credits",
    )

    tags = field(
        ListField(StringField()),
        description="Some keywords to help in search",
    )
    datasets = field(
        ListField(
            field(
                ReferenceField("Dataset", reverse_delete_rule=PULL),
                nested_fields=dataset_fields,
            )
        ),
        description="The post datasets",
    )
    reuses = field(
        ListField(ReferenceField("Reuse", reverse_delete_rule=PULL)),
        description="The post reuses",
    )

    owner = field(
        ReferenceField("User"),
        nested_fields=user_ref_fields,
        readonly=True,
        allow_null=True,
        description="The owner user",
    )
    published = field(
        DateTimeField(),
        readonly=True,
        sortable=True,
        description="The post publication date",
    )

    body_type = field(
        StringField(choices=list(BODY_TYPES), default="markdown", required=False),
    )

    kind = field(
        StringField(choices=list(POST_KINDS), default="news", required=False),
        filterable={},
        description="Post kind (news or page)",
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

    def clean(self):
        if self.body_type != "blocs" and not self.content:
            raise ValidationError("content is required when body_type is 'markdown' or 'html'")

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


# Exclude blocs from paginated list endpoint — blocs are only returned on detail
_post_page_mask = "data{{{0}}},*".format(",".join(k for k in Post.__read_fields__ if k != "blocs"))
Post.__page_fields__.__mask__ = _post_page_mask
