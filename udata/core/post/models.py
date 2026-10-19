from flask import url_for
from flask_storage.mongo import ImageField
from mongoengine import DENY, PULL
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
from udata.core.edito_blocs.base import Bloc
from udata.core.linkable import Linkable
from udata.core.reuse.models import Reuse
from udata.core.storages import default_image_basename, images
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.errors import FieldValidationError
from udata.mongo.queryset import UDataQuerySet
from udata.mongo.slug_fields import SlugField
from udata.mongo.url_field import URLField
from udata.uris import cdata_url

from .api_fields import post_ancestor_fields
from .constants import BODY_TYPES, IMAGE_SIZES, POST_KINDS
from .permissions import PostReadPermission

__all__ = ("Post",)


def check_chosen_slug(slug, obj, is_update, **_kwargs):
    """Runs on the slug already normalized by `SlugField.from_input`."""
    # Left empty at creation, the slug is derived from the name
    if slug is None and not is_update:
        return
    # Cleared on update, or with nothing left once normalized, it would be saved empty:
    # `SlugField` is exempted from the `required` check.
    if not slug:
        raise FieldValidationError(_("The slug must contain letters or digits"), field="slug")
    # Rejected rather than suffixed like a derived slug: the post would be published under
    # a URL nobody asked for.
    if Post.objects(slug=slug, id__ne=obj.id).count():
        raise FieldValidationError(_("This slug is already used by another post"), field="slug")


class PostQuerySet(UDataQuerySet):
    def visible(self):
        return self(published__ne=None)


@generate_fields(
    searchable=True,
    additional_sorts=[
        {"key": "created_at", "value": "created_at"},
        {"key": "modified", "value": "last_modified"},
    ],
    default_sort="-published",
    page_mask_exclude=["blocs"],
)
class Post(Datetimed, Linkable, Document[PostQuerySet]):
    name = field(
        StringField(max_length=255, required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        # No `update`: a renamed post keeps its URL, which only changes when the slug is set
        SlugField(max_length=255, required=True, populate_from="name", follow=True),
        checks=[check_chosen_slug],
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
        ListField(ReferenceField(Reuse, reverse_delete_rule=PULL)),
        description="The post reuses",
    )

    owner = field(
        ReferenceField("User"),
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

    parent = field(
        # DENY: otherwise sub-pages would keep a dangling reference and every read of them
        # would fail. The API checks it first, this covers the deletions made elsewhere.
        ReferenceField("self", reverse_delete_rule=DENY),
        nested_fields=post_ancestor_fields,
        allow_null=True,
        description="The parent page, only for pages",
    )

    meta = {
        "ordering": ["-created_at"],
        "indexes": [
            "-created_at",
            "-published",
            "parent",
            {
                "fields": ["$name", "$headline", "$content"],
                "default_language": "french",
                "weights": {"name": 10, "headline": 5, "content": 4},
            },
        ],
        "queryset_class": PostQuerySet,
    }

    verbose_name = _("post")

    @property
    def is_visible(self):
        return self.published is not None

    @property
    def permissions(self):
        return {"read": PostReadPermission(self)}

    @property
    @field(
        nested_fields=post_ancestor_fields,
        as_list=True,
        description="The ancestor pages, from the root page to the parent",
    )
    def ancestors(self) -> list["Post"]:
        ancestors = []
        seen = set()
        ancestor = self.parent
        # Stops on an id already met: `clean()` rejects cycles, but two concurrent updates
        # (A under B, B under A) each pass it against the other's previous parent. Without
        # this, every read of these posts would loop forever.
        while ancestor and ancestor.id not in seen:
            seen.add(ancestor.id)
            ancestors.insert(0, ancestor)
            ancestor = ancestor.parent
        return ancestors

    @property
    @field(description="The page path, made of the slugs of its ancestors and its own")
    def path(self) -> str:
        return "/".join(post.slug for post in [*self.ancestors, self])

    def clean(self):
        if self.body_type != "blocs" and not self.content:
            raise ValidationError("content is required when body_type is 'markdown' or 'html'")

        if self.parent:
            if self.kind != "page" or self.parent.kind != "page":
                raise ValidationError(
                    "Only a page can have a parent, and its parent must be a page",
                    field_name="parent",
                )
            if any(ancestor.id == self.id for ancestor in self.ancestors):
                raise ValidationError("A page cannot be its own ancestor", field_name="parent")
            # A published page exposes its ancestors (name, slug in its path): a draft
            # parent would leak through it.
            if self.published and not self.parent.published:
                raise ValidationError(
                    "A published page cannot be under an unpublished page", field_name="parent"
                )

        if self.id:
            children = Post.objects(parent=self.id)
            if self.kind != "page" and children.count():
                raise ValidationError("A page with sub-pages must stay a page", field_name="kind")
            if not self.published and children.visible().count():
                raise ValidationError(
                    "A page with published sub-pages cannot be unpublished", field_name="published"
                )

    def __str__(self):
        return self.name or ""

    def self_web_url(self, **kwargs):
        if self.kind == "page":
            return cdata_url(f"/pages/{self.path}", **kwargs)
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
