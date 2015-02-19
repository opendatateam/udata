# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from collections import OrderedDict

from blinker import Signal
from flask import url_for
from mongoengine.signals import pre_save, post_save

from udata.models import db, WithMetrics, Issue, Follow, SpatialCoverage
from udata.i18n import lazy_gettext as _
from udata.utils import hash_url


__all__ = (
    'License', 'Resource', 'Dataset', 'Checksum',
    'DatasetIssue', 'FollowDataset',
    'UPDATE_FREQUENCIES', 'RESOURCE_TYPES',
)

UPDATE_FREQUENCIES = {
    'punctual': _('Punctual'),
    'realtime': _('Real time'),
    'daily': _('Daily'),
    'weekly': _('Weekly'),
    'fortnighly': _('Fortnighly'),
    'monthly': _('Monthly'),
    'bimonthly': _('Bimonthly'),
    'quarterly': _('Quarterly'),
    'biannual': _('Biannual'),
    'annual': _('Annual'),
    'biennial': _('Biennial'),
    'triennial': _('Triennial'),
    'quinquennial': _('Quinquennial'),
    'unknown': _('Unknown'),
}

DEFAULT_FREQUENCY = 'unknown'

RESOURCE_TYPES = OrderedDict([
    ('file', _('Uploaded file')),
    ('remote', _('Remote file')),
    ('api', _('API')),
])

CHECKSUM_TYPES = ('sha1', 'sha2', 'sha256', 'md5', 'crc')
DEFAULT_CHECKSUM_TYPE = 'sha1'


class License(db.Document):
    id = db.StringField(primary_key=True)
    created_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    title = db.StringField(required=True)
    slug = db.SlugField(required=True, populate_from='title')
    url = db.URLField()
    maintainer = db.StringField()
    flags = db.ListField(db.StringField())

    active = db.BooleanField()

    def __unicode__(self):
        return self.title


class DatasetQuerySet(db.BaseQuerySet):
    def visible(self):
        return self(private__ne=True, resources__0__exists=True, deleted=None)

    def hidden(self):
        return self(db.Q(private=True) | db.Q(resources__0__exists=False) | db.Q(deleted__ne=None))


class Checksum(db.EmbeddedDocument):
    type = db.StringField(choices=CHECKSUM_TYPES)
    value = db.StringField()

    def to_mongo(self, *args, **kwargs):
        if bool(self.value):
            return super(Checksum, self).to_mongo()


class Resource(WithMetrics, db.EmbeddedDocument):
    id = db.AutoUUIDField()
    title = db.StringField(verbose_name="Title", required=True)
    description = db.StringField()
    type = db.StringField(choices=RESOURCE_TYPES.keys(), default='file', required=True)
    url = db.StringField()
    urlhash = db.StringField()
    checksum = db.EmbeddedDocumentField(Checksum)
    format = db.StringField()
    mime = db.StringField()
    size = db.IntField()
    owner = db.ReferenceField('User')

    created_at = db.DateTimeField(default=datetime.datetime.now, required=True)
    modified = db.DateTimeField(default=datetime.datetime.now, required=True)
    published = db.DateTimeField(default=datetime.datetime.now, required=True)
    deleted = db.DateTimeField()

    on_added = Signal()
    on_deleted = Signal()

    def clean(self):
        super(Resource, self).clean()
        if not self.urlhash or 'url' in self._get_changed_fields():
            self.urlhash = hash_url(self.url)


class Dataset(WithMetrics, db.Datetimed, db.Document):
    title = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='title', update=True)
    description = db.StringField(required=True, default='')
    license = db.ReferenceField('License')

    tags = db.ListField(db.StringField())
    resources = db.ListField(db.EmbeddedDocumentField(Resource))
    community_resources = db.ListField(db.EmbeddedDocumentField(Resource))

    private = db.BooleanField()
    owner = db.ReferenceField('User', reverse_delete_rule=db.NULLIFY)
    organization = db.ReferenceField('Organization', reverse_delete_rule=db.NULLIFY)
    supplier = db.ReferenceField('Organization', reverse_delete_rule=db.NULLIFY)

    frequency = db.StringField(choices=UPDATE_FREQUENCIES.keys())
    temporal_coverage = db.EmbeddedDocumentField(db.DateRange)
    spatial = db.EmbeddedDocumentField(SpatialCoverage)

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.ExtrasField()

    featured = db.BooleanField(required=True, default=False)

    deleted = db.DateTimeField()

    def __str__(self):
        return self.title or ''

    __unicode__ = __str__

    meta = {
        'allow_inheritance': True,
        'indexes': [
            '-created_at',
            'slug',
            'organization',
            'supplier',
            'resources.id',
            'resources.urlhash',
        ],
        'ordering': ['-created_at'],
        'queryset_class': DatasetQuerySet,
    }

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    verbose_name = _('dataset')

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

    @property
    def display_url(self):
        return url_for('datasets.show', dataset=self)

    @property
    def external_url(self):
        return url_for('datasets.show', dataset=self, _external=True)

    @property
    def image_url(self):
        if self.organization:
            return self.organization.logo.url
        elif self.owner:
            return self.owner.avatar.url

    @property
    def frequency_label(self):
        return UPDATE_FREQUENCIES.get(self.frequency or 'unknown', UPDATE_FREQUENCIES['unknown'])

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)


pre_save.connect(Dataset.pre_save, sender=Dataset)
post_save.connect(Dataset.post_save, sender=Dataset)


class DatasetIssue(Issue):
    subject = db.ReferenceField(Dataset)


class FollowDataset(Follow):
    following = db.ReferenceField(Dataset)
