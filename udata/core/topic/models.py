from flask import url_for

from mongoengine.signals import pre_save
from udata.models import db
from udata.search import reindex
from udata.tasks import as_task_param


__all__ = ('Topic', )


class Topic(db.Document):
    name = db.StringField(required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name',
                        update=True, follow=True)
    description = db.StringField()
    tags = db.ListField(db.StringField())
    color = db.IntField()

    tags = db.ListField(db.StringField())
    datasets = db.ListField(
        db.ReferenceField('Dataset', reverse_delete_rule=db.PULL))
    reuses = db.ListField(
        db.ReferenceField('Reuse', reverse_delete_rule=db.PULL))

    owner = db.ReferenceField('User')
    featured = db.BooleanField()
    private = db.BooleanField()
    extras = db.ExtrasField()

    def __str__(self):
        return self.name

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        try:
            original_doc = sender.objects.get(id=document.id)
            datasets_list_dif = list(set(original_doc.datasets).symmetric_difference(set(document.datasets)))
            reuses_list_dif = list(set(original_doc.reuses).symmetric_difference(set(document.reuses)))
        except cls.DoesNotExist:
            datasets_list_dif = document.datasets
            reuses_list_dif = document.reuses
        if datasets_list_dif:
            for dataset in datasets_list_dif:
                reindex.delay(*as_task_param(dataset))
        if reuses_list_dif:
            for reuse in reuses_list_dif:
                reindex.delay(*as_task_param(reuse))

    @property
    def display_url(self):
        return url_for('topics.display', topic=self)


pre_save.connect(Topic.pre_save, sender=Topic)
