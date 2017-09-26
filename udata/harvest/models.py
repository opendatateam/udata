# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
from datetime import datetime
from urlparse import urlparse

from werkzeug import cached_property

from udata.models import db, Dataset
from udata.i18n import lazy_gettext as _


HARVEST_FREQUENCIES = OrderedDict((
    ('manual', _('Manual')),
    ('monthly', _('Monthly')),
    ('weekly', _('Weekly')),
    ('daily', _('Daily')),
))

HARVEST_JOB_STATUS = OrderedDict((
    ('pending', _('Pending')),
    ('initializing', _('Initializing')),
    ('initialized', _('Initialized')),
    ('processing', _('Processing')),
    ('done', _('Done')),
    ('done-errors', _('Done with errors')),
    ('failed', _('Failed')),
))

HARVEST_ITEM_STATUS = OrderedDict((
    ('pending', _('Pending')),
    ('started', _('Started')),
    ('done', _('Done')),
    ('failed', _('Failed')),
    ('skipped', _('Skipped')),
))

DEFAULT_HARVEST_FREQUENCY = 'manual'
DEFAULT_HARVEST_JOB_STATUS = 'pending'
DEFAULT_HARVEST_ITEM_STATUS = 'pending'


class HarvestError(db.EmbeddedDocument):
    '''Store harvesting errors'''
    created_at = db.DateTimeField(default=datetime.now, required=True)
    message = db.StringField()
    details = db.StringField()


class HarvestItem(db.EmbeddedDocument):
    remote_id = db.StringField()
    dataset = db.ReferenceField(Dataset)
    status = db.StringField(choices=HARVEST_ITEM_STATUS.keys(),
                            default=DEFAULT_HARVEST_ITEM_STATUS, required=True)
    created = db.DateTimeField(default=datetime.now, required=True)
    started = db.DateTimeField()
    ended = db.DateTimeField()
    errors = db.ListField(db.EmbeddedDocumentField(HarvestError))
    args = db.ListField(db.StringField())
    kwargs = db.DictField()


VALIDATION_ACCEPTED = 'accepted'
VALIDATION_REFUSED = 'refused'
VALIDATION_PENDING = 'pending'

VALIDATION_STATES = {
    VALIDATION_PENDING: _('Pending'),
    VALIDATION_ACCEPTED: _('Accepted'),
    VALIDATION_REFUSED: _('Refused'),
}


class HarvestSourceValidation(db.EmbeddedDocument):
    '''Store harvest source validation details'''
    state = db.StringField(choices=VALIDATION_STATES.keys(),
                           default=VALIDATION_PENDING,
                           required=True)
    by = db.ReferenceField('User')
    on = db.DateTimeField()
    comment = db.StringField()


class HarvestSourceQuerySet(db.OwnedQuerySet):
    def visible(self):
        return self(deleted=None)


class HarvestSource(db.Owned, db.Document):
    name = db.StringField(max_length=255)
    slug = db.SlugField(max_length=255, required=True, unique=True,
                        populate_from='name', update=True)
    description = db.StringField()
    url = db.StringField(required=True)
    backend = db.StringField()
    config = db.DictField()
    periodic_task = db.ReferenceField('PeriodicTask',
                                      reverse_delete_rule=db.NULLIFY)
    created_at = db.DateTimeField(default=datetime.now, required=True)
    frequency = db.StringField(choices=HARVEST_FREQUENCIES.keys(),
                               default=DEFAULT_HARVEST_FREQUENCY,
                               required=True)
    active = db.BooleanField(default=True)
    validation = db.EmbeddedDocumentField(HarvestSourceValidation,
                                          default=HarvestSourceValidation)

    deleted = db.DateTimeField()

    @property
    def domain(self):
        parsed = urlparse(self.url)
        return parsed.netloc.split(':')[0]

    @classmethod
    def get(cls, ident):
        return cls.objects(slug=ident).first() or cls.objects.get(pk=ident)

    def get_last_job(self):
        return HarvestJob.objects(source=self).order_by('-created').first()

    @cached_property
    def last_job(self):
        return self.get_last_job()

    @property
    def schedule(self):
        if not self.periodic_task:
            return
        return self.periodic_task.schedule_display

    meta = {
        'indexes': [
            '-created_at',
            'slug',
            ('deleted', '-created_at'),
        ] + db.Owned.meta['indexes'],
        'ordering': ['-created_at'],
        'queryset_class': HarvestSourceQuerySet,
    }

    def __unicode__(self):
        return self.name or ''


class HarvestJob(db.Document):
    '''Keep track of harvestings'''
    created = db.DateTimeField(default=datetime.now, required=True)
    started = db.DateTimeField()
    ended = db.DateTimeField()
    status = db.StringField(choices=HARVEST_JOB_STATUS.keys(),
                            default=DEFAULT_HARVEST_JOB_STATUS, required=True)
    errors = db.ListField(db.EmbeddedDocumentField(HarvestError))
    items = db.ListField(db.EmbeddedDocumentField(HarvestItem))
    source = db.ReferenceField(HarvestSource, reverse_delete_rule=db.NULLIFY)

    meta = {
        'indexes': [
            '-created',
            'source',
            ('source', '-created')
        ],
        'ordering': ['-created'],
    }
