from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlparse

from werkzeug import cached_property

from udata.models import db, Dataset
from udata.i18n import lazy_gettext as _

# Register harvest extras
Dataset.extras.register('harvest:source_id', db.StringField)
Dataset.extras.register('harvest:remote_id', db.StringField)
Dataset.extras.register('harvest:domain', db.StringField)
Dataset.extras.register('harvest:last_update', db.DateTimeField)
Dataset.extras.register('remote_url', db.URLField)


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
    ('archived', _('Archived'))
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
    status = db.StringField(choices=list(HARVEST_ITEM_STATUS),
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
    state = db.StringField(choices=list(VALIDATION_STATES),
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
    frequency = db.StringField(choices=list(HARVEST_FREQUENCIES),
                               default=DEFAULT_HARVEST_FREQUENCY,
                               required=True)
    active = db.BooleanField(default=True)
    autoarchive = db.BooleanField(default=True)
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

    def get_last_job(self, reduced=False):
        qs = HarvestJob.objects(source=self)
        if reduced:
            qs = qs.exclude('source', 'items', 'errors', 'data')
            qs = qs.no_dereference()
        return qs.order_by('-created').first()

    @cached_property
    def last_job(self):
        return self.get_last_job(reduced=True)

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

    def __str__(self):
        return self.name or ''


class HarvestJob(db.Document):
    '''Keep track of harvestings'''
    created = db.DateTimeField(default=datetime.now, required=True)
    started = db.DateTimeField()
    ended = db.DateTimeField()
    status = db.StringField(choices=list(HARVEST_JOB_STATUS),
                            default=DEFAULT_HARVEST_JOB_STATUS, required=True)
    errors = db.ListField(db.EmbeddedDocumentField(HarvestError))
    items = db.ListField(db.EmbeddedDocumentField(HarvestItem))
    source = db.ReferenceField(HarvestSource, reverse_delete_rule=db.CASCADE)
    data = db.DictField()

    meta = {
        'indexes': [
            '-created',
            'source',
            ('source', '-created')
        ],
        'ordering': ['-created'],
    }
