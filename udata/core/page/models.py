from flask import url_for
from mongoengine.fields import DateTimeField, EmbeddedDocumentListField, ListField, StringField
from mongoengine.signals import post_delete

from udata.api_fields import field, generate_fields
from udata.core.edito_blocs.base import Bloc
from udata.core.linkable import Linkable
from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.slug_fields import SlugField

from .api_fields import page_permissions_fields

__all__ = ("Page",)


class PageQuerySet(OwnedQuerySet):
    def visible(self):
        return self(published__ne=None)


def filter_by_topic(base_query, filter_value):
    from udata.core.topic.models import Topic

    topic = Topic.objects(id=filter_value).first()
    if topic is None:
        return base_query.none()
    return base_query.filter(id__in=topic.get_nested_elements_ids("Page"))


@generate_fields(
    searchable=True,
    default_sort="-created_at",
    page_mask_exclude=["blocs"],
    standalone_filters=[
        {
            "key": "topic",
            "type": str,
            "constraints": ["objectid"],
            "query": filter_by_topic,
            "help": "Only the pages attached to this topic",
        },
    ],
)
class Page(Datetimed, Linkable, Owned, Document[PageQuerySet]):
    """A user-or-org owned page made of blocs, a draft until published"""

    verbose_name = _("page")

    name = field(
        StringField(max_length=255, required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        readonly=True,
    )
    description = field(
        StringField(),
        description="A short plain text summary, used for SEO",
    )
    blocs = field(
        EmbeddedDocumentListField(Bloc),
        generic=True,
    )
    tags = field(
        ListField(StringField()),
        filterable={"key": "tag"},
        description="Some keywords to help in search",
    )
    published = field(
        DateTimeField(),
        readonly=True,
        sortable=True,
        description="The page publication date, unset for a draft",
    )

    meta = {
        "indexes": [
            "-created_at",
            "slug",
            "-published",
            {
                "fields": ["$name"],
                "default_language": "french",
            },
        ]
        + Owned.meta["indexes"],
        "ordering": ["-created_at"],
        "queryset_class": PageQuerySet,
    }

    @classmethod
    def post_delete(cls, sender, document, **kwargs):
        """Remove the topic elements pointing to a deleted page"""
        from udata.core.topic.models import TopicElement

        TopicElement.objects(element=document).delete()

    def __str__(self):
        return self.name or ""

    def self_web_url(self, **kwargs):
        # No front for pages: `url_for` falls back to the API url
        return None

    def self_api_url(self, **kwargs):
        return url_for(
            "api.page", page=self._link_id(**kwargs), **self._self_api_url_kwargs(**kwargs)
        )

    @field(description="The API URI for this page", show_as_ref=True)
    def uri(self):
        return self.self_api_url()

    @property
    def is_visible(self):
        return self.published is not None

    @property
    @field(nested_fields=page_permissions_fields)
    def permissions(self):
        from .permissions import PageEditPermission, PageReadPermission

        return {
            "delete": PageEditPermission(self),
            "edit": PageEditPermission(self),
            "read": PageReadPermission(self),
        }


post_delete.connect(Page.post_delete, sender=Page)
