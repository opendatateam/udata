from blinker import Signal
from mongoengine.signals import post_save, pre_save

from udata.api_fields import field
from udata.core.activity.models import Auditable
from udata.core.owned import Owned, OwnedQuerySet
from udata.models import SpatialCoverage, db
from udata.search import reindex

__all__ = ("Topic",)


class Topic(db.Datetimed, Auditable, db.Document, Owned):
    name = field(db.StringField(required=True))
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        auditable=False,
    )
    description = field(db.StringField())
    tags = field(db.ListField(db.StringField()))
    color = field(db.IntField())

    datasets = field(db.ListField(db.LazyReferenceField("Dataset", reverse_delete_rule=db.PULL)))
    reuses = field(db.ListField(db.LazyReferenceField("Reuse", reverse_delete_rule=db.PULL)))

    featured = field(db.BooleanField(default=False), auditable=False)
    private = field(db.BooleanField())
    extras = field(db.ExtrasField(), auditable=False)

    spatial = field(db.EmbeddedDocumentField(SpatialCoverage))

    meta = {
        "indexes": ["$name", "created_at", "slug"] + Owned.meta["indexes"],
        "ordering": ["-created_at"],
        "auto_create_index_on_save": True,
        "queryset_class": OwnedQuerySet,
    }

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()

    def __str__(self):
        return self.name

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        # Try catch is to prevent the mechanism to crash at the
        # creation of the Topic, where an original state does not exist.
        try:
            original_doc = sender.objects.get(id=document.id)
            # Get the diff between the original and current datasets
            datasets_list_dif = set(original_doc.datasets) ^ set(document.datasets)
        except cls.DoesNotExist:
            datasets_list_dif = document.datasets
        for dataset in datasets_list_dif:
            reindex.delay("Dataset", str(dataset.pk))

    def count_discussions(self):
        # There are no metrics on Topic to store discussions count
        pass

    def self_web_url(self, **kwargs):
        # Useful for Discussions to call self_web_url on their `subject`
        return None


pre_save.connect(Topic.pre_save, sender=Topic)
post_save.connect(Topic.post_save, sender=Topic)
