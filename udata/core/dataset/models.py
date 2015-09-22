# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta

from collections import OrderedDict

from blinker import signal
from flask import url_for
from mongoengine.signals import pre_save, post_save
from werkzeug import cached_property

from udata.models import (
    db, WithMetrics, BadgeMixin, Discussion, Follow, Issue,
    SpatialCoverage
)
from udata.i18n import lazy_gettext as _
from udata.utils import hash_url

from .croquemort import check_url_from_cache, check_url_from_group


__all__ = (
    'License', 'Resource', 'Dataset', 'Checksum',
    'DatasetIssue', 'DatasetDiscussion', 'FollowDataset',
    'UPDATE_FREQUENCIES', 'RESOURCE_TYPES',
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
CLOSED_FORMATS = ('pdf', 'doc', 'word', 'xls', 'excel')


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

    def check_availability(self, group):
        """Check if a resource is reachable against a Croquemort server.

        Return a boolean.
        """
        if self.type == 'remote':
            # We perform a quick check for performances matters.
            error, response = check_url_from_cache(self.url, group)
            if error or int(response.get('status', 500)) >= 500:
                return False
            else:
                return True
        else:
            return True  # We consider that API cases (types) are OK.

    @property
    def is_available(self):
        return self.check_availability(group=None)


class Dataset(WithMetrics, BadgeMixin, db.Datetimed, db.Document):
    title = db.StringField(max_length=255, required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from='title', update=True)
    description = db.StringField(required=True, default='')
    license = db.ReferenceField('License')

    tags = db.ListField(db.StringField())
    resources = db.ListField(db.EmbeddedDocumentField(Resource))
    community_resources = db.ListField(db.EmbeddedDocumentField(Resource))

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

    __badges__ = {
        PIVOTAL_DATA: _('Pivotal data'),
    }

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

    def check_availability(self):
        """Check if resources from that dataset are available.

        Return a list of booleans.
        """
        # First, we try to retrieve all data from the group (slug).
        error, response = check_url_from_group(self.slug)
        if error:
            # The group is unknown, the check will be performed by resource.
            return [resource.check_availability(self.slug)
                    for resource in self.resources]
        else:
            return [int(url_infos['status']) == 200
                    for url_infos in response['urls']]

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
            result['frequency'] = self.frequency
            result['update_in'] = -(self.next_update - datetime.now()).days
        if self.tags:
            result['tags_count'] = len(self.tags)
        if self.description:
            result['description_length'] = len(self.description)
        if self.resources:
            result['has_resources'] = True
            result['has_only_closed_formats'] = all(
                resource.closed_format for resource in self.resources)
            result['has_unavailable_resources'] = not all(
                self.check_availability())
        discussions = DatasetDiscussion.objects(subject=self.id)
        if discussions:
            result['discussions'] = len(discussions)
            result['has_untreated_discussions'] = not all(
                discussion.person_involved(self.owner)
                for discussion in discussions)
        result['score'] = self.compute_quality_score(result)
        return result

    def compute_quality_score(self, quality):
        """Compute the score related to the quality of that dataset."""
        score = 0
        UNIT = 2
        if 'frequency' in quality:
            # TODO: should be related to frequency.
            if quality['update_in'] < 0:
                score += UNIT
            else:
                score -= UNIT
        if 'tags_count' in quality:
            if quality['tags_count'] > 3:
                score += UNIT
        if 'description_length' in quality:
            if quality['description_length'] > 100:
                score += UNIT
        if 'has_resources' in quality:
            if quality['has_only_closed_formats']:
                score -= UNIT
            else:
                score += UNIT
            if quality['has_unavailable_resources']:
                score -= UNIT
            else:
                score += UNIT
        if 'discussions' in quality:
            if quality['has_untreated_discussions']:
                score -= UNIT
            else:
                score += UNIT
        if score < 0:
            return 0
        return score

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
