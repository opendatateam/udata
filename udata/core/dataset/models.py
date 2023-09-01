import logging

from datetime import datetime, timedelta
from collections import OrderedDict
from urllib.parse import urlparse

from blinker import signal
from dateutil.parser import parse as parse_dt
from flask import current_app
from mongoengine import DynamicEmbeddedDocument, ValidationError as MongoEngineValidationError
from mongoengine.signals import pre_save, post_save
from mongoengine.fields import DateTimeField
from stringdist import rdlevenshtein
from werkzeug.utils import cached_property
import requests

from udata.app import cache
from udata.core import storages
from udata.frontend.markdown import mdstrip
from udata.models import db, WithMetrics, BadgeMixin, SpatialCoverage
from udata.i18n import lazy_gettext as _
from udata.utils import get_by, hash_url, to_naive_datetime
from udata.uris import ValidationError, endpoint_for
from udata.uris import validate as validate_url

from .preview import get_preview_url
from .exceptions import (
    SchemasCatalogNotFoundException, SchemasCacheUnavailableException
)

__all__ = (
    'License', 'Resource', 'Dataset', 'Checksum', 'CommunityResource',
    'UPDATE_FREQUENCIES', 'LEGACY_FREQUENCIES', 'RESOURCE_FILETYPES',
    'PIVOTAL_DATA', 'DEFAULT_LICENSE', 'RESOURCE_TYPES',
    'ResourceSchema'
)

log = logging.getLogger(__name__)

#: Udata frequencies with their labels
#:
#: See: http://dublincore.org/groups/collections/frequency/
UPDATE_FREQUENCIES = OrderedDict([                              # Dublin core equivalent
    ('unknown', _('Unknown')),                        # N/A
    ('punctual', _('Punctual')),                      # N/A
    ('continuous', _('Real time')),                   # freq:continuous
    ('hourly', _('Hourly')),                          # N/A
    ('fourTimesADay', _('Four times a day')),         # N/A
    ('threeTimesADay', _('Three times a day')),       # N/A
    ('semidaily', _('Semidaily')),                    # N/A
    ('daily', _('Daily')),                            # freq:daily
    ('fourTimesAWeek', _('Four times a week')),       # N/A
    ('threeTimesAWeek', _('Three times a week')),     # freq:threeTimesAWeek
    ('semiweekly', _('Semiweekly')),                  # freq:semiweekly
    ('weekly', _('Weekly')),                          # freq:weekly
    ('biweekly', _('Biweekly')),                      # freq:bimonthly
    ('threeTimesAMonth', _('Three times a month')),   # freq:threeTimesAMonth
    ('semimonthly', _('Semimonthly')),                # freq:semimonthly
    ('monthly', _('Monthly')),                        # freq:monthly
    ('bimonthly', _('Bimonthly')),                    # freq:bimonthly
    ('quarterly', _('Quarterly')),                    # freq:quarterly
    ('threeTimesAYear', _('Three times a year')),     # freq:threeTimesAYear
    ('semiannual', _('Biannual')),                    # freq:semiannual
    ('annual', _('Annual')),                          # freq:annual
    ('biennial', _('Biennial')),                      # freq:biennial
    ('triennial', _('Triennial')),                    # freq:triennial
    ('quinquennial', _('Quinquennial')),              # N/A
    ('irregular', _('Irregular')),                    # freq:irregular
])

#: Map legacy frequencies to currents
LEGACY_FREQUENCIES = {
    'fortnighly': 'biweekly',
    'biannual': 'semiannual',
    'realtime': 'continuous',
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
    ('main', _('Main file')),
    ('documentation', _('Documentation')),
    ('update', _('Update')),
    ('api', _('API')),
    ('code', _('Code repository')),
    ('other', _('Other')),
])

RESOURCE_FILETYPE_FILE = 'file'
RESOURCE_FILETYPES = OrderedDict([
    (RESOURCE_FILETYPE_FILE, _('Uploaded file')),
    ('remote', _('Remote file')),
])

CHECKSUM_TYPES = ('sha1', 'sha2', 'sha256', 'md5', 'crc')
DEFAULT_CHECKSUM_TYPE = 'sha1'

PIVOTAL_DATA = 'pivotal-data'
CLOSED_FORMATS = ('pdf', 'doc', 'docx', 'word', 'xls', 'excel', 'xlsx')

# Maximum acceptable Damerau-Levenshtein distance
# used to guess license
# (ie. number of allowed character changes)
MAX_DISTANCE = 2

SCHEMA_CACHE_DURATION = 60 * 5  # In seconds

TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000


def get_json_ld_extra(key, value):
    '''Serialize an extras key, value pair into JSON-LD'''
    value = value.serialize() if hasattr(value, 'serialize') else value
    return {
        '@type': 'http://schema.org/PropertyValue',
        'name': key,
        'value': value,
    }


class HarvestDatasetMetadata(DynamicEmbeddedDocument):
    backend = db.StringField()
    created_at = db.DateTimeField()
    modified_at = db.DateTimeField()
    source_id = db.StringField()
    remote_id = db.StringField()
    domain = db.StringField()
    last_update = db.DateTimeField()
    remote_url = db.URLField()
    uri = db.StringField()
    dct_identifier = db.StringField()
    archived_at = db.DateTimeField()
    archived = db.StringField()


class HarvestResourceMetadata(DynamicEmbeddedDocument):
    created_at = db.DateTimeField()
    modified_at = db.DateTimeField()
    uri = db.StringField()


class License(db.Document):
    # We need to declare id explicitly since we do not use the default
    # value set by Mongo.
    id = db.StringField(primary_key=True)
    created_at = db.DateTimeField(default=datetime.utcnow, required=True)
    title = db.StringField(required=True)
    alternate_titles = db.ListField(db.StringField())
    slug = db.SlugField(required=True, populate_from='title')
    url = db.URLField()
    alternate_urls = db.ListField(db.URLField())
    maintainer = db.StringField()
    flags = db.ListField(db.StringField())

    active = db.BooleanField()

    def __str__(self):
        return self.title

    @classmethod
    def guess(cls, *strings, **kwargs):
        '''
        Try to guess a license from a list of strings.

        Accept a `default` keyword argument which will be
        the default fallback license.
        '''
        license = None
        for string in strings:
            license = cls.guess_one(string)
            if license:
                break
        return license or kwargs.get('default')

    @classmethod
    def guess_one(cls, text):
        '''
        Try to guess license from a string.

        Try to exact match on identifier then slugified title
        and fallback on edit distance ranking (after slugification)
        '''
        if not text:
            return
        qs = cls.objects
        text = text.strip().lower()  # Stored identifiers are lower case
        slug = cls.slug.slugify(text)  # Use slug as it normalize string
        license = qs(
            db.Q(id__iexact=text) | db.Q(slug=slug) | db.Q(url__iexact=text)
            | db.Q(alternate_urls__iexact=text)
        ).first()

        if license is None:
            # If we're dealing with an URL, let's try some specific stuff
            # like getting rid of trailing slash and scheme mismatch
            try:
                url = validate_url(text)
            except ValidationError:
                pass
            else:
                parsed = urlparse(url)
                path = parsed.path.rstrip('/')
                query = f'{parsed.netloc}{path}'
                license = qs(db.Q(url__icontains=query) | db.Q(alternate_urls__contains=query)).first()

        if license is None:
            # Try to single match `slug` with a low Damerau-Levenshtein distance
            computed = ((l, rdlevenshtein(l.slug, slug)) for l in cls.objects)
            candidates = [l for l, d in computed if d <= MAX_DISTANCE]
            # If there is more that one match, we cannot determinate
            # which one is closer to safely choose between candidates
            if len(candidates) == 1:
                license = candidates[0]

        if license is None:
            # Try to match `title` with a low Damerau-Levenshtein distance
            computed = ((l, rdlevenshtein(l.title.lower(), text)) for l in cls.objects)
            candidates = [l for l, d in computed if d <= MAX_DISTANCE]
            # If there is more that one match, we cannot determinate
            # which one is closer to safely choose between candidates
            if len(candidates) == 1:
                license = candidates[0]

        if license is None:
            # Try to single match `alternate_titles` with a low Damerau-Levenshtein distance
            computed = (
                (l, rdlevenshtein(cls.slug.slugify(t), slug))
                for l in cls.objects
                for t in l.alternate_titles
            )
            candidates = [l for l, d in computed if d <= MAX_DISTANCE]
            # If there is more that one license matching, we cannot determinate
            # which one is closer to safely choose between candidates
            if len(set(candidates)) == 1:
                license = candidates[0]
        return license

    @classmethod
    def default(cls):
        return cls.objects(id=DEFAULT_LICENSE['id']).first()


class DatasetQuerySet(db.OwnedQuerySet):
    def visible(self):
        return self(private__ne=True, resources__0__exists=True,
                    deleted=None, archived=None)

    def hidden(self):
        return self(db.Q(private=True) |
                    db.Q(resources__0__exists=False) |
                    db.Q(deleted__ne=None) |
                    db.Q(archived__ne=None))


class Checksum(db.EmbeddedDocument):
    type = db.StringField(choices=CHECKSUM_TYPES, required=True)
    value = db.StringField(required=True)

    def to_mongo(self, *args, **kwargs):
        if bool(self.value):
            return super(Checksum, self).to_mongo()


class ResourceMixin(object):
    id = db.AutoUUIDField(primary_key=True)
    title = db.StringField(verbose_name="Title", required=True)
    description = db.StringField()
    filetype = db.StringField(
        choices=list(RESOURCE_FILETYPES), default='file', required=True)
    type = db.StringField(
        choices=list(RESOURCE_TYPES), default='main', required=True)
    url = db.URLField(required=True)
    urlhash = db.StringField()
    checksum = db.EmbeddedDocumentField(Checksum)
    format = db.StringField()
    mime = db.StringField()
    filesize = db.IntField()  # `size` is a reserved keyword for mongoengine.
    fs_filename = db.StringField()
    extras = db.ExtrasField()
    harvest = db.EmbeddedDocumentField(HarvestResourceMetadata)
    schema = db.DictField()

    created_at_internal = db.DateTimeField(default=datetime.utcnow, required=True)
    last_modified_internal = db.DateTimeField(default=datetime.utcnow, required=True)
    deleted = db.DateTimeField()

    @property
    def internal(self):
        return {
            'created_at_internal': self.created_at_internal,
            'last_modified_internal': self.last_modified_internal
        }

    @property
    def created_at(self):
        return self.harvest.created_at if self.harvest and self.harvest.created_at else self.created_at_internal

    @property
    def last_modified(self):
        if self.harvest and self.harvest.modified_at and to_naive_datetime(self.harvest.modified_at) < datetime.utcnow():
            return max([self.last_modified_internal, to_naive_datetime(self.harvest.modified_at)])
        if self.filetype == 'remote' and self.extras.get('analysis:last-modified-at'):
            return to_naive_datetime(self.extras.get('analysis:last-modified-at'))
        return self.last_modified_internal

    def clean(self):
        super(ResourceMixin, self).clean()
        if not self.urlhash or 'url' in self._get_changed_fields():
            self.urlhash = hash_url(self.url)
        if self.schema and (not bool('name' in self.schema) ^ bool('url' in self.schema)):
            raise MongoEngineValidationError('Schema must have at least a name or an url. Having both is not allowed.')

    @cached_property  # Accessed at least 2 times in front rendering
    def preview_url(self):
        return get_preview_url(self)

    @property
    def closed_or_no_format(self):
        """
        Return True if the specified format is in CLOSED_FORMATS or
        no format has been specified.
        """
        return not self.format or self.format.lower() in CLOSED_FORMATS

    def check_availability(self):
        '''
        Return the check status from extras if any.

        NB: `unknown` will evaluate to True in the aggregate checks using
        `all([])` (dataset, organization, user).
        '''
        return self.extras.get('check:available', 'unknown')

    def need_check(self):
        '''Does the resource needs to be checked against its linkchecker?

        We check unavailable resources often, unless they go over the
        threshold. Available resources are checked less and less frequently
        based on their historical availability.
        '''
        min_cache_duration, max_cache_duration, ko_threshold = [
            current_app.config.get(k) for k in (
                'LINKCHECKING_MIN_CACHE_DURATION',
                'LINKCHECKING_MAX_CACHE_DURATION',
                'LINKCHECKING_UNAVAILABLE_THRESHOLD',
            )
        ]
        count_availability = self.extras.get('check:count-availability', 1)
        is_available = self.check_availability()
        if is_available == 'unknown':
            return True
        elif is_available or count_availability > ko_threshold:
            delta = min(min_cache_duration * count_availability,
                        max_cache_duration)
        else:
            delta = min_cache_duration
        if self.extras.get('check:date'):
            limit_date = datetime.utcnow() - timedelta(minutes=delta)
            check_date = self.extras['check:date']
            if not isinstance(check_date, datetime):
                try:
                    check_date = parse_dt(check_date)
                except (ValueError, TypeError):
                    return True
            if check_date >= limit_date:
                return False
        return True

    @property
    def latest(self):
        '''
        Permanent link to the latest version of this resource.

        If this resource is updated and `url` changes, this property won't.
        '''
        return endpoint_for('datasets.resource', 'api.resource_redirect', id=self.id, _external=True)

    @cached_property
    def json_ld(self):

        result = {
            '@type': 'DataDownload',
            '@id': str(self.id),
            'url': self.latest,
            'name': self.title or _('Nameless resource'),
            'contentUrl': self.url,
            'dateCreated': self.created_at.isoformat(),
            'dateModified': self.last_modified.isoformat(),
            'extras': [get_json_ld_extra(*item)
                       for item in self.extras.items()],
        }

        if 'views' in self.metrics:
            result['interactionStatistic'] = {
                '@type': 'InteractionCounter',
                'interactionType': {
                    '@type': 'DownloadAction',
                },
                'userInteractionCount': self.metrics['views']
            }

        if self.format:
            result['encodingFormat'] = self.format

        if self.filesize:
            result['contentSize'] = self.filesize

        if self.mime:
            result['fileFormat'] = self.mime

        if self.description:
            result['description'] = mdstrip(self.description)

        return result


class Resource(ResourceMixin, WithMetrics, db.EmbeddedDocument):
    '''
    Local file, remote file or API provided by the original provider of the
    dataset
    '''
    on_added = signal('Resource.on_added')
    on_deleted = signal('Resource.on_deleted')

    __metrics_keys__ = [
        'views',
    ]

    @property
    def dataset(self):
        try:
            self._instance.id  # try to access attr from parent instance
            return self._instance
        except ReferenceError:  # weakly-referenced object no longer exists
            log.warning('Weakly referenced object for resource.dataset no longer exists, '
                        'using a poor performance query instead.')
            return Dataset.objects(resources__id=self.id).first()

    def save(self, *args, **kwargs):
        if not self.dataset:
            raise RuntimeError('Impossible to save an orphan resource')
        self.dataset.save(*args, **kwargs)


class Dataset(WithMetrics, BadgeMixin, db.Owned, db.Document):
    title = db.StringField(required=True)
    acronym = db.StringField(max_length=128)
    # /!\ do not set directly the slug when creating or updating a dataset
    # this will break the search indexation
    slug = db.SlugField(max_length=255, required=True, populate_from='title',
                        update=True, follow=True)
    description = db.StringField(required=True, default='')
    license = db.ReferenceField('License')

    tags = db.TagListField()
    resources = db.ListField(db.EmbeddedDocumentField(Resource))

    private = db.BooleanField(default=False)
    frequency = db.StringField(choices=list(UPDATE_FREQUENCIES.keys()))
    frequency_date = db.DateTimeField(verbose_name=_('Future date of update'))
    temporal_coverage = db.EmbeddedDocumentField(db.DateRange)
    spatial = db.EmbeddedDocumentField(SpatialCoverage)

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.ExtrasField()
    harvest = db.EmbeddedDocumentField(HarvestDatasetMetadata)

    featured = db.BooleanField(required=True, default=False)

    created_at_internal = DateTimeField(verbose_name=_('Creation date'),
                                        default=datetime.utcnow, required=True)
    last_modified_internal = DateTimeField(verbose_name=_('Last modification date'),
                                           default=datetime.utcnow, required=True)
    deleted = db.DateTimeField()
    archived = db.DateTimeField()

    def __str__(self):
        return self.title or ''

    __badges__ = {
        PIVOTAL_DATA: _('Pivotal data'),
    }

    __metrics_keys__ = [
        'discussions',
        'reuses',
        'followers',
        'views',
    ]

    meta = {
        'indexes': [
            '$title',
            'created_at_internal',
            'last_modified_internal',
            'metrics.reuses',
            'metrics.followers',
            'metrics.views',
            'slug',
            'resources.id',
            'resources.urlhash',
        ] + db.Owned.meta['indexes'],
        'ordering': ['-created_at_internal'],
        'queryset_class': DatasetQuerySet,
        'auto_create_index_on_save': True
    }

    before_save = signal('Dataset.before_save')
    after_save = signal('Dataset.after_save')
    on_create = signal('Dataset.on_create')
    on_update = signal('Dataset.on_update')
    before_delete = signal('Dataset.before_delete')
    after_delete = signal('Dataset.after_delete')
    on_delete = signal('Dataset.on_delete')
    on_archive = signal('Dataset.on_archive')
    on_resource_added = signal('Dataset.on_resource_added')
    on_resource_updated = signal('Dataset.on_resource_updated')
    on_resource_removed = signal('Dataset.on_resource_removed')

    verbose_name = _('dataset')

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        if 'post_save' in kwargs.get('ignores', []):
            return
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)
        if document.deleted:
            cls.on_delete.send(document)

    def clean(self):
        super(Dataset, self).clean()
        if self.frequency in LEGACY_FREQUENCIES:
            self.frequency = LEGACY_FREQUENCIES[self.frequency]

    def url_for(self, *args, **kwargs):
        return endpoint_for('datasets.show', 'api.dataset', dataset=self, *args, **kwargs)

    display_url = property(url_for)

    @property
    def is_visible(self):
        return not self.is_hidden

    @property
    def is_hidden(self):
        return (len(self.resources) == 0 or self.private or self.deleted
                or self.archived)

    @property
    def full_title(self):
        if not self.acronym:
            return self.title
        return '{title} ({acronym})'.format(**self._data)

    @property
    def external_url(self):
        return self.url_for(_external=True)

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

        Return a list of (boolean or 'unknown')
        """
        # Only check remote resources.
        remote_resources = [resource
                            for resource in self.resources
                            if resource.filetype == 'remote']
        if not remote_resources:
            return []
        return [resource.check_availability() for resource in remote_resources]

    @property
    def created_at(self):
        return self.harvest.created_at if self.harvest and self.harvest.created_at else self.created_at_internal

    @property
    def last_modified(self):
        if (self.harvest and self.harvest.modified_at and
                to_naive_datetime(self.harvest.modified_at) < datetime.utcnow()):
            return max([self.last_modified_internal, to_naive_datetime(self.harvest.modified_at)])
        return self.last_modified_internal

    @property
    def last_update(self):
        """
        Use the more recent date we would have on resources (harvest, modified).
        Default to dataset last_modified if no resource.
        """
        if self.resources:
            return max([res.last_modified for res in self.resources])
        else:
            return self.last_modified

    @property
    def next_update(self):
        """Compute the next expected update date,
        given the frequency and last_update.
        Return None if the frequency is not handled.

        We consider frequencies that have a number of
        occurences on a timespan to be irregularry divided
        in the timespan and expect a next update before the end
        of the timespan.

        Ex: the next update for a threeTimesAday freq is not
        every 8 hours, but is maximum 24 hours later.
        """
        delta = None
        if self.frequency == 'hourly':
            delta = timedelta(hours=1)
        elif self.frequency in ['fourTimesADay', 'threeTimesADay', 'semidaily', 'daily']:
            delta = timedelta(days=1)
        elif self.frequency in ['fourTimesAWeek', 'threeTimesAWeek', 'semiweekly', 'weekly']:
            delta = timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            delta = timedelta(weeks=2)
        elif self.frequency in ['threeTimesAMonth', 'semimonthly', 'monthly']:
            delta = timedelta(days=31)
        elif self.frequency == 'bimonthly':
            delta = timedelta(days=31 * 2)
        elif self.frequency == 'quarterly':
            delta = timedelta(days=365 / 4)
        elif self.frequency in ['threeTimesAYear', 'semiannual', 'annual']:
            delta = timedelta(days=365)
        elif self.frequency == 'biennial':
            delta = timedelta(days=365 * 2)
        elif self.frequency == 'triennial':
            delta = timedelta(days=365 * 3)
        elif self.frequency == 'quinquennial':
            delta = timedelta(days=365 * 5)
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
        if not self.id:
            # Quality is only relevant on saved Datasets
            return result

        result['license'] = True if self.license else False
        result['temporal_coverage'] = True if self.temporal_coverage else False
        result['spatial'] = True if self.spatial else False

        result['update_frequency'] = self.frequency and self.frequency != 'unknown'
        if self.next_update:
            result['update_fulfilled_in_time'] = (
                True if -(self.next_update - datetime.utcnow()).days <= 0 else False
            )
        elif self.frequency in ['continuous', 'irregular', 'punctual']:
            # For these frequencies, we don't expect regular updates or can't quantify them.
            # Thus we consider the update_fulfilled_in_time quality criterion to be true.
            result['update_fulfilled_in_time'] = True

        result['dataset_description_quality'] = (
            True if len(self.description) > current_app.config.get('QUALITY_DESCRIPTION_LENGTH')
            else False
        )

        if self.resources:
            result['has_resources'] = True
            result['has_open_format'] = not all(
                resource.closed_or_no_format for resource in self.resources)
            result['all_resources_available'] = all(self.check_availability())
            resource_doc = False
            resource_desc = False
            for resource in self.resources:
                if resource.type == 'documentation':
                    resource_doc = True
                if resource.description:
                    resource_desc = True
            result['resources_documentation'] = resource_doc or resource_desc

        result['score'] = self.compute_quality_score(result)
        return result

    @staticmethod
    def normalize_score(score):
        """
        Normalize score by dividing it by the quality max score.
        Make sure to update QUALITY_MAX_SCORE accordingly if the max score changes.
        """
        QUALITY_MAX_SCORE = 9
        return score / QUALITY_MAX_SCORE

    def compute_quality_score(self, quality):
        """
        Compute the score related to the quality of that dataset.
        The score is normalized between 0 and 1.

        Make sure to update normalize_score if the max score changes.
        """
        score = 0
        UNIT = 1
        if quality['license']:
            score += UNIT
        if quality['temporal_coverage']:
            score += UNIT
        if quality['spatial']:
            score += UNIT
        if quality['update_frequency']:
            score += UNIT
        if 'update_fulfilled_in_time' in quality:
            if quality['update_fulfilled_in_time']:
                score += UNIT
        if quality['dataset_description_quality']:
            score += UNIT
        if 'has_resources' in quality:
            if quality['has_open_format']:
                score += UNIT
            if quality['all_resources_available']:
                score += UNIT
            if quality['resources_documentation']:
                score += UNIT
        return self.normalize_score(score)

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    def add_resource(self, resource):
        '''Perform an atomic prepend for a new resource'''
        resource.validate()
        self.update(__raw__={
            '$push': {
                'resources': {
                    '$each': [resource.to_mongo()],
                    '$position': 0
                }
            }
        })
        self.reload()
        self.on_resource_added.send(self.__class__, document=self, resource_id=resource.id)

    def update_resource(self, resource):
        '''Perform an atomic update for an existing resource'''
        index = self.resources.index(resource)
        data = {
            'resources__{index}'.format(index=index): resource
        }
        self.update(**data)
        self.reload()
        self.on_resource_updated.send(self.__class__, document=self, resource_id=resource.id)

    def remove_resource(self, resource):
        # Deletes resource's file from file storage
        if resource.fs_filename is not None:
            storages.resources.delete(resource.fs_filename)

        self.resources.remove(resource)
        self.on_resource_removed.send(self.__class__, document=self, resource_id=resource.id)

    @property
    def community_resources(self):
        return self.id and CommunityResource.objects.filter(dataset=self) or []

    @cached_property
    def json_ld(self):
        result = {
            '@context': 'http://schema.org',
            '@type': 'Dataset',
            '@id': str(self.id),
            'alternateName': self.slug,
            'dateCreated': self.created_at.isoformat(),
            'dateModified': self.last_modified.isoformat(),
            'url': endpoint_for('datasets.show', 'api.dataset', dataset=self, _external=True),
            'name': self.title,
            'keywords': ','.join(self.tags),
            'distribution': [resource.json_ld for resource in self.resources],
            # Theses values are not standard
            'contributedDistribution': [
                resource.json_ld for resource in self.community_resources
            ],
            'extras': [get_json_ld_extra(*item)
                       for item in self.extras.items()],
        }

        if self.description:
            result['description'] = mdstrip(self.description)

        if self.license and self.license.url:
            result['license'] = self.license.url

        if self.organization:
            author = self.organization.json_ld
        elif self.owner:
            author = self.owner.json_ld
        else:
            author = None

        if author:
            result['author'] = author

        return result

    @property
    def internal(self):
        return {
            'created_at_internal': self.created_at_internal,
            'last_modified_internal': self.last_modified_internal
        }

    @property
    def views_count(self):
        return self.metrics.get('views', 0)

    def count_discussions(self):
        from udata.models import Discussion
        self.metrics['discussions'] = Discussion.objects(subject=self, closed=None).count()
        self.save()

    def count_reuses(self):
        from udata.models import Reuse
        self.metrics['reuses'] = Reuse.objects(datasets=self).visible().count()
        self.save()

    def count_followers(self):
        from udata.models import Follow
        self.metrics['followers'] = Follow.objects(until=None).followers(self).count()
        self.save()


pre_save.connect(Dataset.pre_save, sender=Dataset)
post_save.connect(Dataset.post_save, sender=Dataset)


class CommunityResource(ResourceMixin, WithMetrics, db.Owned, db.Document):
    '''
    Local file, remote file or API added by the community of the users to the
    original dataset
    '''
    dataset = db.ReferenceField(Dataset, reverse_delete_rule=db.NULLIFY)

    __metrics_keys__ = [
        'views',
    ]

    meta = {
        'ordering': ['-created_at_internal'],
        'queryset_class': db.OwnedQuerySet,
    }

    @property
    def from_community(self):
        return True


class ResourceSchema(object):
    @staticmethod
    @cache.memoize(timeout=SCHEMA_CACHE_DURATION)
    def objects():
        '''
        Get a list of schemas from a schema catalog endpoint.

        This has a double layer of cache:
        - @cache.cached decorator w/ short lived cache for normal operations
        - a long terme cache w/o timeout to be able to always render some content
        '''
        endpoint = current_app.config.get('SCHEMA_CATALOG_URL')
        if endpoint is None:
            return []

        cache_key = 'schema-catalog-objects'
        try:
            response = requests.get(endpoint, timeout=5)
            # do not cache 404 and forward status code
            if response.status_code == 404:
                raise SchemasCatalogNotFoundException(f'Schemas catalog does not exist at {endpoint}')
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            log.exception(f'Error while getting schema catalog from {endpoint}')
            content = cache.get(cache_key)
        else:
            schemas = response.json().get('schemas', [])
            content = [
                {
                    'id': s['name'],
                    'label': s['title'],
                    'versions': [d['version_name'] for d in s['versions']],
                } for s in schemas
            ]
            cache.set(cache_key, content)
        # no cached version or no content
        if not content:
            log.error(f'No content found inc. from cache for schema catalog')
            raise SchemasCacheUnavailableException('No content in cache for schema catalog')
        return content


def get_resource(id):
    '''Fetch a resource given its UUID'''
    dataset = Dataset.objects(resources__id=id).first()
    if dataset:
        return get_by(dataset.resources, 'id', id)
    else:
        return CommunityResource.objects(id=id).first()
