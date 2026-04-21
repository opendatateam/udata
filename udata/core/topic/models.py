from blinker import Signal
from flask import url_for
from mongoengine.errors import DoesNotExist
from mongoengine.fields import (
    BooleanField,
    EmbeddedDocumentField,
    GenericReferenceField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)
from mongoengine.signals import post_delete, post_save

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.linkable import Linkable
from udata.core.owned import Owned, OwnedQuerySet
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.spatial.models import SpatialCoverage
from udata.i18n import lazy_gettext as _
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.errors import FieldValidationError
from udata.mongo.extras_fields import ExtrasField
from udata.mongo.slug_fields import SlugField
from udata.search import reindex
from udata.tasks import as_task_param

__all__ = ("Topic", "TopicElement")


def check_title_or_element_required(value, obj, data, **_kwargs):
    title = data.get("title", getattr(obj, "title", None))
    element = data.get("element", getattr(obj, "element", None))
    if not title and not element:
        raise FieldValidationError(
            _("A topic element must have a title or an element."),
            field="element",
        )


check_title_or_element_required.run_even_if_missing = True


@generate_fields()
class TopicElement(Auditable, Document):
    title = field(StringField(required=False))
    description = field(
        StringField(required=False),
        markdown=True,
    )
    tags = field(ListField(StringField()))
    extras = field(ExtrasField())
    element = field(
        GenericReferenceField(choices=["Dataset", "Reuse", "Dataservice"]),
        nested_fields=api.model_reference,
        allow_null=True,
        checks=[check_title_or_element_required],
    )
    # Not exposed in the API (not wrapped with field()), only used internally.
    topic = ReferenceField("Topic", required=True)

    meta = {
        "indexes": [
            {
                "fields": ["$title", "$description"],
            }
        ],
        "auto_create_index_on_save": True,
    }

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    on_delete = Signal()

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        """Trigger reindex when element is saved"""
        # Call parent post_save for Auditable functionality
        super().post_save(sender, document, **kwargs)
        if document.topic and document.element and hasattr(document.element, "id"):
            reindex.delay(*as_task_param(document.element))

    @classmethod
    def post_delete(cls, sender, document, **kwargs):
        """Trigger reindex when element is deleted"""
        try:
            if document.topic and document.element and hasattr(document.element, "id"):
                reindex.delay(*as_task_param(document.element))
        except DoesNotExist:
            # Topic might have been deleted, causing dereferencing to fail
            pass
        cls.on_delete.send(document)


@generate_fields()
class Topic(Datetimed, Auditable, Linkable, Document[OwnedQuerySet], Owned):
    name = field(StringField(required=True), show_as_ref=True)
    slug = field(
        SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        auditable=False,
        readonly=True,
    )
    description = field(
        StringField(),
        markdown=True,
    )
    tags = field(ListField(StringField()))
    color = field(IntField())

    featured = field(BooleanField(default=False), auditable=False)
    private = field(BooleanField())
    extras = field(ExtrasField(), auditable=False)

    spatial = field(
        EmbeddedDocumentField(SpatialCoverage),
        nested_fields=spatial_coverage_fields,
        allow_null=True,
    )

    meta = {
        "indexes": [
            {
                "fields": ["$name", "$description"],
            },
            "created_at",
            "slug",
        ]
        + Owned.meta["indexes"],
        "ordering": ["-created_at"],
        "auto_create_index_on_save": True,
        "queryset_class": OwnedQuerySet,
    }

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()

    @classmethod
    def post_delete(cls, sender, document, **kwargs):
        """Delete associated TopicElements when a Topic is deleted"""
        TopicElement.objects(topic=document).delete()

    def __str__(self):
        return self.name

    def count_discussions(self):
        # There are no metrics on Topic to store discussions count
        pass

    @property
    def elements(self):
        """Get elements associated with this topic"""
        return TopicElement.objects(topic=self)

    def get_nested_elements_ids(self, cls: str) -> set[str]:
        """Optimized query to get objects ids from related elements, filtered by class."""
        # Return empty set if topic doesn't have an ID yet
        if not self.id:
            return set()

        return set(
            str(elem["element"]["_ref"].id)
            for elem in TopicElement.objects.filter(topic=self, __raw__={"element._cls": cls})
            .fields(element=1)
            .no_dereference()
            .as_pymongo()
        )

    def self_web_url(self, **kwargs):
        # Useful for Discussions to call self_web_url on their `subject`
        return None

    def self_api_url(self, **kwargs):
        return url_for(
            "apiv2.topic",
            topic=self._link_id(**kwargs),
            **self._self_api_url_kwargs(**kwargs),
        )

    @field(description="The topic API URI")
    def uri(self):
        return self.self_api_url()


post_save.connect(Topic.post_save, sender=Topic)
post_save.connect(TopicElement.post_save, sender=TopicElement)
post_delete.connect(Topic.post_delete, sender=Topic)
post_delete.connect(TopicElement.post_delete, sender=TopicElement)
