# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta

from collections import OrderedDict

from blinker import signal
from flask import url_for
from mongoengine.signals import pre_save, post_save
from werkzeug import cached_property

from udata.models import (
    db, WithMetrics, Badge, BadgeMixin, Discussion, Follow, Issue,
    SpatialCoverage
)
from udata.i18n import lazy_gettext as _
from udata.utils import hash_url


__all__ = (
    'License', 'Resource', 'Dataset', 'Checksum',
    'DatasetIssue', 'DatasetDiscussion', 'DatasetBadge', 'FollowDataset',
    'UPDATE_FREQUENCIES', 'RESOURCE_TYPES', 'DATASET_BADGE_KINDS', 'C3',
    'PIVOTAL_DATA', 'DEFAULT_LICENSE'
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

DEFAULT_LICENSE = {
    'id': 'notspecified',
    'title': "License Not Specified",
    'flags': ["generic"],
    'maintainer': None,
    'url': None,
    'active': True,
}

RESOURCE_TYPES = OrderedDict([
    ('file', _('Uploaded file')),
    ('remote', _('Remote file')),
    ('api', _('API')),
])

CHECKSUM_TYPES = ('sha1', 'sha2', 'sha256', 'md5', 'crc')
DEFAULT_CHECKSUM_TYPE = 'sha1'

PIVOTAL_DATA = 'pivotal-data'
C3 = 'c3'
DATASET_BADGE_KINDS = {
    PIVOTAL_DATA: _('Pivotal data'),
    C3: _('C³'),
}

CLOSED_FORMATS = ('pdf', 'doc', 'word', 'xls', 'excel')


class DatasetBadge(Badge):
    kind = db.StringField(choices=DATASET_BADGE_KINDS.keys(), required=True)

    def __html__(self):
        return unicode(DATASET_BADGE_KINDS[self.kind])


class License(db.Document):
    id = db.StringField(primary_key=True)
    created_at = db.DateTimeField(default=datetime.now, required=True)
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
        return self(db.Q(private=True)
                    | db.Q(resources__0__exists=False)
                    | db.Q(deleted__ne=None))

    def owned_by(self, *owners):
        Qs = db.Q()
        for owner in owners:
            Qs |= db.Q(owner=owner) | db.Q(organization=owner)
        return self(Qs)


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
    type = db.StringField(
        choices=RESOURCE_TYPES.keys(), default='file', required=True)
    url = db.StringField()
    urlhash = db.StringField()
    checksum = db.EmbeddedDocumentField(Checksum)
    format = db.StringField()
    mime = db.StringField()
    size = db.IntField()
    owner = db.ReferenceField('User')

    created_at = db.DateTimeField(default=datetime.now, required=True)
    modified = db.DateTimeField(default=datetime.now, required=True)
    published = db.DateTimeField(default=datetime.now, required=True)
    deleted = db.DateTimeField()

    on_added = signal('Resource.on_added')
    on_deleted = signal('Resource.on_deleted')

    def clean(self):
        super(Resource, self).clean()
        if not self.urlhash or 'url' in self._get_changed_fields():
            self.urlhash = hash_url(self.url)

    @property
    def closed_format(self):
        """Return True if the specified format is in CLOSED_FORMATS."""
        return self.format.lower() in CLOSED_FORMATS


class Dataset(WithMetrics, BadgeMixin, db.Datetimed, db.Document):
    title = db.StringField(max_length=255, required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from='title', update=True)
    description = db.StringField(required=True, default='')
    license = db.ReferenceField('License')

    tags = db.ListField(db.StringField())
    resources = db.ListField(db.EmbeddedDocumentField(Resource))
    community_resources = db.ListField(db.EmbeddedDocumentField(Resource))
    badges = db.ListField(db.EmbeddedDocumentField(DatasetBadge))

    private = db.BooleanField()
    owner = db.ReferenceField('User', reverse_delete_rule=db.NULLIFY)
    organization = db.ReferenceField('Organization',
                                     reverse_delete_rule=db.NULLIFY)
    supplier = db.ReferenceField('Organization',
                                 reverse_delete_rule=db.NULLIFY)

    frequency = db.StringField(choices=UPDATE_FREQUENCIES.keys())
    frequency_date = db.DateTimeField(verbose_name=_('Future date of update'))
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

    before_save = signal('Dataset.before_save')
    after_save = signal('Dataset.after_save')
    on_create = signal('Dataset.on_create')
    on_update = signal('Dataset.on_update')
    before_delete = signal('Dataset.before_delete')
    after_delete = signal('Dataset.after_delete')
    on_delete = signal('Dataset.on_delete')

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
        return UPDATE_FREQUENCIES.get(self.frequency or 'unknown',
                                      UPDATE_FREQUENCIES['unknown'])

    @property
    def last_update(self):
        if self.resources:
            return max(resource.published for resource in self.resources)
        else:
            return self.last_modified

    @property
    def next_update(self):
        """Compute the next expected update date,

        given the frequency and last_update.
        Return None if the frequency is not handled.
        """
        delta = None
        if self.frequency == 'daily':
            delta = timedelta(days=1)
        elif self.frequency == 'weekly':
            delta = timedelta(weeks=1)
        elif self.frequency == 'fortnighly':
            delta = timedelta(weeks=2)
        elif self.frequency == 'monthly':
            delta = timedelta(weeks=4)
        elif self.frequency == 'bimonthly':
            delta = timedelta(weeks=4 * 2)
        elif self.frequency == 'quarterly':
            delta = timedelta(weeks=52 / 4)
        elif self.frequency == 'biannual':
            delta = timedelta(weeks=52 / 2)
        elif self.frequency == 'annual':
            delta = timedelta(weeks=52)
        elif self.frequency == 'biennial':
            delta = timedelta(weeks=52 * 2)
        elif self.frequency == 'triennial':
            delta = timedelta(weeks=52 * 3)
        elif self.frequency == 'quinquennial':
            delta = timedelta(weeks=52 * 5)
        if delta is None:
            return
        else:
            return self.last_update + delta

    @cached_property
    def quality(self):
        """Return a dict filled with metrics related to the inner

        quality of the dataset:

            * number of tags
            * description length
            * and so on
        """
        result = {}
        if self.next_update:
            result['next_update'] = self.next_update
        if self.tags:
            result['tags_count'] = len(self.tags)
        if self.description:
            result['description_length'] = len(self.description)
        if self.resources:
            result['has_only_closed_formats'] = all(
                resource.closed_format for resource in self.resources)
        discussions = DatasetDiscussion.objects(subject=self)
        if discussions:
            result['has_untreated_discussions'] = not all(
                discussion.person_involved(self.owner)
                for discussion in discussions)
        return result

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    def add_resource(self, resource):
        '''Perform an atomic prepend for a new resource'''
        self.update(__raw__={
            '$push': {
                'resources': {
                    '$each': [resource.to_mongo()],
                    '$position': 0
                }
            }
        })
        self.reload()
        post_save.send(self.__class__, document=self)

    def add_community_resource(self, resource):
        '''Perform an atomic prepend for a new resource'''
        self.update(__raw__={
            '$push': {
                'community_resources': {
                    '$each': [resource.to_mongo()],
                    '$position': 0
                }
            }
        })
        self.reload()
        post_save.send(self.__class__, document=self)


pre_save.connect(Dataset.pre_save, sender=Dataset)
post_save.connect(Dataset.post_save, sender=Dataset)


class DatasetIssue(Issue):
    subject = db.ReferenceField(Dataset)


class DatasetDiscussion(Discussion):
    subject = db.ReferenceField(Dataset)


class FollowDataset(Follow):
    following = db.ReferenceField(Dataset)
