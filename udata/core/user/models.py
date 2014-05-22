# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from blinker import Signal
from flask import url_for, g
from flask.ext.security import UserMixin, RoleMixin, MongoEngineUserDatastore

from udata.models import db, WithMetrics


__all__ = ('User', 'Role', 'datastore')


def populate_slug(user):
    return ' '.join([user.first_name, user.last_name])


# TODO: use simple text for role
class Role(db.Document, RoleMixin):
    ADMIN = 'admin'
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)

    def __str__(self):
        return self.name

    __unicode__ = __str__


class User(db.Document, WithMetrics,UserMixin):
    slug = db.SlugField(max_length=255, required=True, populate_from=populate_slug)
    email = db.StringField(max_length=255, required=True)
    password = db.StringField()
    active = db.BooleanField()
    roles = db.ListField(db.ReferenceField(Role), default=[])

    first_name = db.StringField(max_length=255, required=True)
    last_name = db.StringField(max_length=255, required=True)

    avatar_url = db.URLField()
    website = db.URLField()
    about = db.StringField()

    prefered_language = db.StringField()

    created_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    confirmed_at = db.DateTimeField()
    last_login_at = db.DateTimeField()
    current_login_at = db.DateTimeField()
    last_login_ip = db.StringField()
    current_login_ip = db.StringField()
    login_count = db.IntField()

    starred_datasets = db.ListField(db.ReferenceField('Dataset'))
    starred_reuses = db.ListField(db.ReferenceField('Reuse'))
    starred_organizations = db.ListField(db.ReferenceField('Organization'))

    ext = db.MapField(db.GenericEmbeddedDocumentField())

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'slug'],
        'ordering': ['-created_at']
    }

    def get_absolute_url(self):
        return url_for('user', slug=self.slug)

    def __unicode__(self):
        return self.fullname

    @property
    def fullname(self):
        return ' '.join((self.first_name, self.last_name))

    @property
    def organizations(self):
        return getattr(g, 'user_orgs', [])

    @property
    def sysadmin(self):
        return bool(getattr(g, 'sysadmin'))


datastore = MongoEngineUserDatastore(db, User, Role)
