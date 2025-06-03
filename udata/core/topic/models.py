from flask import url_for
from mongoengine.signals import pre_save

from udata.core.owned import Owned, OwnedQuerySet
from udata.models import SpatialCoverage, db
from udata.search import reindex

__all__ = ("Topic",)


class TopicElement(db.EmbeddedDocument):
    id = db.AutoUUIDField(primary_key=True)
    title = db.StringField(required=False)
    description = db.StringField(required=False)
    tags = db.ListField(db.StringField())
    extras = db.ExtrasField()
    element = db.GenericReferenceField()


class Topic(db.Document, Owned, db.Datetimed):
    name = db.StringField(required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from="name", update=True, follow=True
    )
    description = db.StringField()
    tags = db.ListField(db.StringField())
    color = db.IntField()

    tags = db.ListField(db.StringField())
    elements = db.EmbeddedDocumentListField(TopicElement)

    featured = db.BooleanField(default=False)
    private = db.BooleanField()
    extras = db.ExtrasField()

    spatial = db.EmbeddedDocumentField(SpatialCoverage)

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

    def __str__(self):
        return self.name

    # TODO: also reindex Reuses (never been done) but Reuse.topic is a different field
    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        # Try catch is to prevent the mechanism to crash at the
        # creation of the Topic, where an original state does not exist.
        try:
            original_doc = sender.objects.get(id=document.id)
            # Get the diff between the original and current datasets
            datasets_list_dif = set(
                elt.element
                for elt in original_doc.elements
                if elt.element.__class__.__name__ == "Dataset"
            ) ^ set(
                elt.element
                for elt in document.elements
                if elt.element.__class__.__name__ == "Dataset"
            )
        except cls.DoesNotExist:
            datasets_list_dif = set(
                elt.element
                for elt in document.elements
                if elt.element.__class__.__name__ == "Dataset"
            )
        for dataset in datasets_list_dif:
            reindex.delay("Dataset", str(dataset.pk))

    @property
    def display_url(self):
        return url_for("topics.display", topic=self)

    def count_discussions(self):
        # There are no metrics on Topic to store discussions count
        pass


pre_save.connect(Topic.pre_save, sender=Topic)
