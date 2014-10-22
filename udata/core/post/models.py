# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import db
from udata.core.storages import images, default_image_basename


__all__ = ('Post', )


IMAGE_SIZES = [100, 50, 25]


class Post(db.Datetimed, db.Document):
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    headline = db.StringField()
    content = db.StringField(required=True)
    image_url = db.StringField()
    image = db.ImageField(fs=images, basename=default_image_basename)

    credit_to = db.StringField()
    credit_url = db.URLField()

    tags = db.ListField(db.StringField())
    datasets = db.ListField(db.ReferenceField('Dataset'))
    reuses = db.ListField(db.ReferenceField('Reuse'))

    owner = db.ReferenceField('User')
    private = db.BooleanField()

    def __unicode__(self):
        return self.name or ''

    @property
    def display_url(self):
        return url_for('posts.show', post=self)
