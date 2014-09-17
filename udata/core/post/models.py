# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import db


__all__ = ('Post', )


class Post(db.Datetimed, db.Document):
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    headline = db.StringField()
    content = db.StringField(required=True)
    image_url = db.StringField()

    credit_to = db.StringField()
    credit_url = db.URLField()

    tags = db.ListField(db.StringField())
    datasets = db.ListField(db.ReferenceField('Dataset'))
    reuses = db.ListField(db.ReferenceField('Reuse'))

    owner = db.ReferenceField('User')
    private = db.BooleanField()

    def __unicode__(self):
        return self.name

    @property
    def display_url(self):
        return url_for('posts.show', post=self)
