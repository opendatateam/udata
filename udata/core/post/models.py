# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.models import db


__all__ = ('Post', )


class Post(db.Datetimed, db.Document):
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    content = db.StringField(required=True)
    image_url = db.StringField()

    credit_to = db.StringField()
    credit_url = db.URLField()

    tags = db.ListField(db.StringField())

    owner = db.ReferenceField('User')
    private = db.BooleanField()

    def __unicode__(self):
        return self.name
