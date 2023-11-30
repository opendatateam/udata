from datetime import datetime
from flask import url_for
from mongoengine.fields import DateTimeField
from mongoengine.signals import pre_save
from udata.models import db
from udata.search import reindex
from udata.tasks import as_task_param


__all__ = ('Topic', )


class Topic(db.Document, db.Owned):
    name = db.StringField(required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name',
                        update=True, follow=True)
    description = db.StringField()
    tags = db.ListField(db.StringField())
    color = db.IntField()

    tags = db.ListField(db.StringField())
    datasets = db.ListField(
        db.LazyReferenceField('Dataset', reverse_delete_rule=db.PULL))
    reuses = db.ListField(
        db.LazyReferenceField('Reuse', reverse_delete_rule=db.PULL))

    featured = db.BooleanField()
    private = db.BooleanField()
    extras = db.ExtrasField()

    created_at = DateTimeField(default=datetime.utcnow, required=True)

    meta = {
        'indexes': [
            '$name',
            'created_at',
            'slug'
        ] + db.Owned.meta['indexes'],
        'ordering': ['-created_at'],
        'auto_create_index_on_save': True
    }

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
            reindex.delay(*as_task_param(dataset.fetch()))

    @property
    def display_url(self):
        return url_for('topics.display', topic=self)

    def count_discussions(self):
        # There are no metrics on Topic to store discussions count
        pass


pre_save.connect(Topic.pre_save, sender=Topic)
