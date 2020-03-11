from flask import url_for

from udata.models import db


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

    def __str__(self):
        return self.name

    @property
    def display_url(self):
        return url_for('topics.display', topic=self)
