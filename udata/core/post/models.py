from flask import url_for
from flask_storage.mongo import ImageField
from mongoengine import DENY, PULL, Q
from mongoengine.errors import ValidationError
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    EmbeddedDocumentListField,
    ListField,
    ReferenceField,
    StringField,
)
from mongoengine.signals import post_delete

from udata.api_fields import field, generate_fields
from udata.auth import Permission
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.permissions import OwnablePermission
from udata.core.edito_blocs.base import Bloc, check_blocs_layout
from udata.core.linkable import Linkable
from udata.core.owned import Owned, OwnedQuerySet
from udata.core.reuse.models import Reuse
from udata.core.storages import default_image_basename, images
from udata.core.topic.models import Topic, TopicElement
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.errors import FieldValidationError
from udata.mongo.slug_fields import SlugField
from udata.mongo.url_field import URLField
from udata.uris import cdata_url

from .api_fields import post_ancestor_fields, post_permissions_fields
from .constants import BODY_TYPES, EXTERNAL_PAGE, IMAGE_SIZES, POST_KINDS
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


class PostQuerySet(OwnedQuerySet):
    def visible(self):
        return self(published__ne=None)

    def visible_by_user(self, user, visible_query: Q):
        """Everything visible to the user: owners only get their own external page drafts."""
        posts = super().visible_by_user(user, visible_query)
        if user.is_anonymous or user.sysadmin:
            return posts
        return posts.filter(visible_query | Q(kind=EXTERNAL_PAGE))


def filter_by_topic(base_query, filter_value):
    topic = Topic.objects(id=filter_value).first()
    if topic is None:
        return base_query.none()
    return base_query.filter(id__in=topic.get_nested_elements_ids("Post"))


@generate_fields(
    searchable=True,
    additional_sorts=[
        {"key": "created_at", "value": "created_at"},
        {"key": "modified", "value": "last_modified"},
    ],
    default_sort="-published",
    page_mask_exclude=["blocs"],
    standalone_filters=[
        {
            "key": "topic",
            "type": str,
            "constraints": ["objectid"],
            "query": filter_by_topic,
            "help": "Only the posts attached to this topic",
        },
    ],
)
class Post(Datetimed, Linkable, Owned, Document[PostQuerySet]):
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
        checks=[check_blocs_layout],
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
        filterable={"key": "tag"},
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
        description="Post kind (news, page or external_page). Only news and pages are shown on the main site.",
    )

    sidemenu = field(
        BooleanField(default=False),
        description="Display a side menu linking to the headings of the post",
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
        ]
        + Owned.meta["indexes"],
        "queryset_class": PostQuerySet,
    }

    verbose_name = _("post")

    @property
    def is_visible(self):
        return self.published is not None

    @property
    def is_external_page(self):
        return self.kind == EXTERNAL_PAGE

    @property
    @field(nested_fields=post_permissions_fields)
    def permissions(self):
        # Editorial posts are only editable by sysadmins, owners edit their external pages
        edit = OwnablePermission(self) if self.is_external_page else Permission()
        return {
            "delete": edit,
            "edit": edit,
            "read": PostReadPermission(self),
        }

    @classmethod
    def post_delete(cls, sender, document, **kwargs):
        """Remove the topic elements pointing to a deleted post"""
        TopicElement.objects(element=document).delete()

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
    def path(self) -> str:
        return "/".join(post.slug for post in [*self.ancestors, self])

    def clean(self):
        super().clean()
        self._check_kind()
        if self.is_external_page:
            # Users can only write blocs, never raw markdown or html
            if self.content or self.body_type == "html":
                raise FieldValidationError(
                    _("External pages only support blocs"), field="body_type"
                )
            self.body_type = "blocs"
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

    def _check_kind(self):
        if self._created or "kind" not in self._get_changed_fields():
            return
        previous = Post.objects.only("kind").get(pk=self.pk).kind
        if previous != self.kind and EXTERNAL_PAGE in (previous, self.kind):
            # Moving a post in or out of external pages would bypass the ownership rules
            raise FieldValidationError(
                _("Cannot change the kind of a post from or to external_page"), field="kind"
            )

    def __str__(self):
        return self.name or ""

    def self_web_url(self, **kwargs):
        if self.is_external_page:
            # Rendered by external sites: `url_for` falls back to the API url
            return None
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


post_delete.connect(Post.post_delete, sender=Post)
