# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Signal
from flask import url_for
from mongoengine.signals import pre_save, post_save

from udata.models import db, WithMetrics
from udata.i18n import lazy_gettext as _


__all__ = ('Organization', 'Team', 'Member', 'ORG_ROLES')


ORG_ROLES = {
    'admin': _('Administrateur'),
    'editor': _('Administrateur'),
}


class OrgUnit(object):
    '''
    Simple mixin holding common fields for all organization units.
    '''
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    description = db.StringField(required=True)
    url = db.URLField(max_length=255)
    image_url = db.URLField(max_length=255)
    extras = db.DictField()


class Team(db.EmbeddedDocument):
    name = db.StringField(required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    description = db.StringField()

    members = db.ListField(db.ReferenceField('User'))


class Member(db.EmbeddedDocument):
    user = db.ReferenceField('User')
    role = db.StringField(choices=ORG_ROLES.keys())


class Organization(WithMetrics, db.Datetimed, db.Document):
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    description = db.StringField(required=True)
    url = db.StringField()
    image_url = db.StringField()

    members = db.ListField(db.EmbeddedDocumentField(Member))
    teams = db.ListField(db.EmbeddedDocumentField(Team))

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.DictField()

    # TODO: Extract into extension
    public_service = db.BooleanField()


    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'slug'],
        'ordering': ['-created_at']
    }

    def get_absolute_url(self):
        return url_for('organizations.show', org=self)

    def __unicode__(self):
        return self.name

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_star = Signal()
    on_unstar = Signal()

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)


pre_save.connect(Organization.pre_save, sender=Organization)
post_save.connect(Organization.post_save, sender=Organization)

