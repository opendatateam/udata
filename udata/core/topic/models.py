from blinker import Signal
from mongoengine.signals import post_save, pre_save

from udata.api_fields import field
from udata.core.activity.models import Auditable
from udata.core.dataset.models import Dataset
from udata.core.owned import Owned, OwnedQuerySet
from udata.core.reuse.models import Reuse
from udata.models import SpatialCoverage, db
from udata.search import reindex

__all__ = ("Topic", "TopicElement")


class TopicElement(db.Document):
    title = field(db.StringField(required=False))
    description = field(db.StringField(required=False))
    tags = field(db.ListField(db.StringField()))
    extras = field(db.ExtrasField())
    element = field(db.GenericReferenceField(choices=[Dataset, Reuse]))

    meta = {
        "indexes": [
            {
                "fields": ["$title", "$description"],
            }
        ],
        "auto_create_index_on_save": True,
    }


class Topic(db.Datetimed, Auditable, db.Document, Owned):
    name = field(db.StringField(required=True))
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        auditable=False,
    )
    description = field(db.StringField())
    tags = field(db.ListField(db.StringField()))
    color = field(db.IntField())

    elements = field(
        db.ListField(
            db.LazyReferenceField("TopicElement", reverse_delete_rule=db.PULL, passthrough=True)
        )
    )

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

    # TODO: also reindex Reuses (never been done) but Reuse.topic is a different field
    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        # Try catch is to prevent the mechanism to crash at the
        # creation of the Topic, where an original state does not exist.
        try:
            original_doc = sender.objects.get(id=document.id)
            original_dataset_ids = original_doc.get_nested_elements_ids("Dataset")
            current_dataset_ids = document.get_nested_elements_ids("Dataset")
            datasets_list_diff = original_dataset_ids ^ current_dataset_ids
        except cls.DoesNotExist:
            datasets_list_diff = document.get_nested_elements_ids("Dataset")

        for dataset_id in datasets_list_diff:
            reindex.delay("Dataset", dataset_id)

    def count_discussions(self):
        # There are no metrics on Topic to store discussions count
        pass

    def get_nested_elements_ids(self, cls: str) -> set[str]:
        """Optimized query to get objects ids from nested elements, filtered by class."""
        return set(
            str(elem["element"]["_ref"].id)
            for elem in TopicElement.objects.filter(
                id__in=[ref.pk for ref in self.elements], __raw__={"element._cls": cls}
            )
            .fields(element=1)
            .as_pymongo()
        )


pre_save.connect(Topic.pre_save, sender=Topic)
post_save.connect(Topic.post_save, sender=Topic)
