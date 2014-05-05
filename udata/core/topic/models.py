# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.models import db


__all__ = ('Topic', )


class Topic(db.Document):
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    description = db.StringField()
    tags = db.ListField(db.StringField())
    color = db.IntField()

    owner = db.ReferenceField('User')
    featured = db.BooleanField()
    private = db.BooleanField()

    def __unicode__(self):
        return self.name
