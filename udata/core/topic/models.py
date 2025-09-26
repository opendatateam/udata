from blinker import Signal
from flask import url_for
from mongoengine.signals import post_delete, post_save

from udata.api_fields import field
from udata.core.activity.models import Auditable
from udata.core.linkable import Linkable
from udata.core.owned import Owned, OwnedQuerySet
from udata.models import SpatialCoverage, db
from udata.search import reindex
from udata.tasks import as_task_param

__all__ = ("Topic", "TopicElement")


class TopicElement(Auditable, db.Document):
    title = field(db.StringField(required=False))
    description = field(db.StringField(required=False))
    tags = field(db.ListField(db.StringField()))
    extras = field(db.ExtrasField())
    element = field(db.GenericReferenceField(choices=["Dataset", "Reuse", "Dataservice"]))
    # Made optional to allow proper form handling with commit=False
    topic = field(db.ReferenceField("Topic", required=False))

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
        if document.topic and document.element and hasattr(document.element, "id"):
            reindex.delay(*as_task_param(document.element))
        cls.on_delete.send(document)


class Topic(db.Datetimed, Auditable, Linkable, db.Document, Owned):
    name = field(db.StringField(required=True))
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        auditable=False,
    )
    description = field(db.StringField())
    tags = field(db.ListField(db.StringField()))
    color = field(db.IntField())

    featured = field(db.BooleanField(default=False), auditable=False)
    private = field(db.BooleanField())
    extras = field(db.ExtrasField(), auditable=False)

    spatial = field(db.EmbeddedDocumentField(SpatialCoverage))

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


post_save.connect(Topic.post_save, sender=Topic)
post_save.connect(TopicElement.post_save, sender=TopicElement)
post_delete.connect(TopicElement.post_delete, sender=TopicElement)
