# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib

from blinker import Signal
from flask import url_for
from mongoengine.signals import pre_save, post_save

from udata.i18n import lazy_gettext as _
from udata.models import db, WithMetrics, Issue

__all__ = ('Reuse', 'REUSE_TYPES', 'ReuseIssue')


REUSE_TYPES = {
    'api': _('API'),
    'application': _('Application'),
    'idea': _('Idea'),
    'news_article': _('News Article'),
    'paper': _('Paper'),
    'post': _('Post'),
    'visualization': _('Visualization'),
}


class ReuseQuerySet(db.BaseQuerySet):
    def visible(self):
        return self(private__ne=True, datasets__0__exists=True, deleted=None)


class Reuse(db.Datetimed, WithMetrics, db.Document):
    title = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='title', update=True)
    description = db.StringField(required=True)
    type = db.StringField(required=True, choices=REUSE_TYPES.keys())
    url = db.StringField(required=True, unique=True)
    urlhash = db.StringField(required=True, unique=True)
    image_url = db.StringField()
    datasets = db.ListField(db.ReferenceField('Dataset'))
    tags = db.ListField(db.StringField())

    private = db.BooleanField()
    owner = db.ReferenceField('User')
    organization = db.ReferenceField('Organization')

    ext = db.MapField(db.GenericEmbeddedDocumentField())

    featured = db.BooleanField()
    deleted = db.DateTimeField()

    def __unicode__(self):
        return self.title

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'owner', 'urlhash'],
        'ordering': ['-created_at'],
        'queryset_class': ReuseQuerySet,
    }

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    @classmethod
    def hash_url(cls, url):
        return hashlib.sha1(url).hexdigest()

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        # auto populate url_sha1 from url
        document.urlhash = cls.hash_url(document.url)
        # Emit before_save
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)

    @property
    def display_url(self):
        return url_for('reuses.show', reuse=self)


pre_save.connect(Reuse.pre_save, sender=Reuse)
post_save.connect(Reuse.post_save, sender=Reuse)


class ReuseIssue(Issue):
    subject = db.ReferenceField(Reuse)
