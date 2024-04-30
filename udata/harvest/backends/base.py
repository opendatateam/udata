import logging
import traceback

from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

import requests

from flask import current_app
from voluptuous import MultipleInvalid, RequiredFieldInvalid

from udata.core.dataset.models import HarvestDatasetMetadata
from udata.models import Dataset
from udata.utils import safe_unicode

from ..exceptions import HarvestException, HarvestSkipException, HarvestValidationError
from ..models import HarvestItem, HarvestJob, HarvestError, archive_harvested_dataset
from ..signals import before_harvest_job, after_harvest_job

log = logging.getLogger(__name__)

# Disable those annoying warnings
requests.packages.urllib3.disable_warnings()


class HarvestFilter(object):
    TYPES = {
        str: 'string',
        bytes: 'string',
        int: 'integer',
        bool: 'boolean',
        UUID: 'uuid',
        datetime: 'date-time',
        date: 'date',
    }

    def __init__(self, label, key, type, description=None):
        if type not in self.TYPES:
            raise TypeError('Unsupported type {0}'.format(type))
        self.label = label
        self.key = key
        self.type = type
        self.description = description

    def as_dict(self):
        return {
            'label': self.label,
            'key': self.key,
            'type': self.TYPES[self.type],
            'description': self.description,
        }


class HarvestFeature(object):
    def __init__(self, key, label, description=None, default=False):
        self.key = key
        self.label = label
        self.description = description
        self.default = default

    def as_dict(self):
        return {
            'key': self.key,
            'label': self.label,
            'description': self.description,
            'default': self.default,
        }


class BaseBackend(object):
    '''Base class for Harvester implementations'''

    name = None
    display_name = None
    verify_ssl = True

    # Define some allowed filters on the backend
    # This a Sequence[HarvestFilter]
    filters = tuple()

    # Define some allowed filters on the backend
    # This a Sequence[HarvestFeature]
    features = tuple()

    def __init__(self, source_or_job, dryrun=False, max_items=None):
        if isinstance(source_or_job, HarvestJob):
            self.source = source_or_job.source
            self.job = source_or_job
        else:
            self.source = source_or_job
            self.job = None
        self.dryrun = dryrun
        self.max_items = max_items or current_app.config['HARVEST_MAX_ITEMS']

    @property
    def config(self):
        return self.source.config

    def head(self, url, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.head(url, headers=headers, **kwargs)

    def get(self, url, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def post(self, url, data, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.post(url, data=data, headers=headers, **kwargs)

    def get_headers(self):
        return {
            # TODO: extract site title and version
            'User-Agent': 'uData/0.1 {0.name}'.format(self),
        }

    def has_feature(self, key):
        try:
            feature = next(f for f in self.features if f.key == key)
        except StopIteration:
            raise HarvestException('Unknown feature {}'.format(key))
        return self.config.get('features', {}).get(key, feature.default)

    def get_filters(self):
        return self.config.get('filters', [])

    def harvest(self):
        '''Start the harvesting process'''
        if self.perform_initialization() is not None:
            self.process_items()
            self.finalize()
        return self.job

    def perform_initialization(self):
        '''Initialize the harvesting for a given job'''
        log.debug('Initializing backend')
        factory = HarvestJob if self.dryrun else HarvestJob.objects.create
        self.job = factory(status='initializing',
                           started=datetime.utcnow(),
                           source=self.source)

        before_harvest_job.send(self)

        try:
            self.initialize()
            self.job.status = 'initialized'
            if not self.dryrun:
                self.job.save()
        except HarvestValidationError as e:
            log.info('Initialization failed for "%s" (%s)',
                     safe_unicode(self.source.name), self.source.backend)
            error = HarvestError(message=safe_unicode(e))
            self.job.errors.append(error)
            self.job.status = 'failed'
            self.end()
            return None
        except Exception as e:
            self.job.status = 'failed'
            error = HarvestError(message=safe_unicode(e))
            self.job.errors.append(error)
            self.end()
            msg = 'Initialization failed for "{0.name}" ({0.backend})'
            log.exception(msg.format(self.source))
            return None

        if self.max_items:
            self.job.items = self.job.items[:self.max_items]

        if self.job.items:
            log.debug('Queued %s items', len(self.job.items))

        return len(self.job.items)

    def initialize(self):
        raise NotImplementedError

    def process_items(self):
        '''Process the data identified in the initialize stage'''
        for item in self.job.items:
            self.process_item(item)

    def process_item(self, item):
        log.debug('Processing: %s', item.remote_id)
        item.status = 'started'
        item.started = datetime.utcnow()
        if not self.dryrun:
            self.job.save()

        try:
            dataset = self.process(item)
            if not dataset.harvest:
                dataset.harvest = HarvestDatasetMetadata()
            dataset.harvest.domain = self.source.domain
            dataset.harvest.remote_id = item.remote_id
            dataset.harvest.source_id = str(self.source.id)
            dataset.harvest.last_update = datetime.utcnow()
            dataset.harvest.backend = self.display_name

            # unset archived status if needed
            if dataset.harvest:
                dataset.harvest.archived_at = None
                dataset.harvest.archived = None
            dataset.archived = None

            # TODO permissions checking
            if not dataset.organization and not dataset.owner:
                if self.source.organization:
                    dataset.organization = self.source.organization
                elif self.source.owner:
                    dataset.owner = self.source.owner

            # TODO: Apply editble mappings

            if self.dryrun:
                dataset.validate()
            else:
                dataset.save()
            item.dataset = dataset
            item.status = 'done'
        except HarvestSkipException as e:
            log.info('Skipped item %s : %s', item.remote_id, safe_unicode(e))
            item.status = 'skipped'
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except HarvestValidationError as e:
            log.info('Error validating item %s : %s', item.remote_id, safe_unicode(e))
            item.status = 'failed'
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except Exception as e:
            log.exception('Error while processing %s : %s',
                          item.remote_id,
                          safe_unicode(e))
            error = HarvestError(message=safe_unicode(e),
                                 details=traceback.format_exc())
            item.errors.append(error)
            item.status = 'failed'

        item.ended = datetime.utcnow()
        if not self.dryrun:
            self.job.save()

    def autoarchive(self):
        '''
        Archive items that exist on the local instance but not on remote platform
        after a grace period of HARVEST_AUTOARCHIVE_GRACE_DAYS days.
        '''
        log.debug('Running autoarchive')
        limit_days = current_app.config['HARVEST_AUTOARCHIVE_GRACE_DAYS']
        limit_date = date.today() - timedelta(days=limit_days)
        remote_ids = [i.remote_id for i in self.job.items if i.status != 'archived']
        q = {
            'harvest__source_id': str(self.source.id),
            'harvest__remote_id__nin': remote_ids,
            'harvest__last_update__lt': limit_date
        }
        local_items_not_on_remote = Dataset.objects.filter(**q)

        for dataset in local_items_not_on_remote:
            if not dataset.harvest.archived_at:
                archive_harvested_dataset(dataset, reason='not-on-remote', dryrun=self.dryrun)
            # add a HarvestItem to the job list (useful for report)
            # even when archiving has already been done (useful for debug)
            item = self.add_item(dataset.harvest.remote_id)
            item.dataset = dataset
            item.status = 'archived'

            if not self.dryrun:
                self.job.save()

    def process(self, item):
        raise NotImplementedError

    def add_item(self, identifier, *args, **kwargs):
        item = HarvestItem(remote_id=str(identifier), args=args, kwargs=kwargs)
        self.job.items.append(item)
        return item

    def finalize(self):
        if self.source.autoarchive:
            self.autoarchive()
        self.job.status = 'done'
        if any(i.status == 'failed' for i in self.job.items):
            self.job.status += '-errors'
        self.end()

    def end(self):
        self.job.ended = datetime.utcnow()
        if not self.dryrun:
            self.job.save()
        after_harvest_job.send(self)

    def get_dataset(self, remote_id):
        '''Get or create a dataset given its remote ID (and its source)
        We first try to match `source_id` to be source domain independent
        '''
        dataset = Dataset.objects(__raw__={
            'harvest.remote_id': remote_id,
            '$or': [
                {'harvest.domain': self.source.domain},
                {'harvest.source_id': str(self.source.id)},
            ],
        }).first()

        if dataset:
            return dataset

        if self.source.organization:
            return Dataset(organization=self.source.organization)
        elif self.source.owner:
            return Dataset(owner=self.source.owner)

        return Dataset()

    def validate(self, data, schema):
        '''Perform a data validation against a given schema.

        :param data: an object to validate
        :param schema: a Voluptous schema to validate against
        '''
        try:
            return schema(data)
        except MultipleInvalid as ie:
            errors = []
            for error in ie.errors:
                if error.path:
                    field = '.'.join(str(p) for p in error.path)
                    path = error.path
                    value = data
                    while path:
                        attr = path.pop(0)
                        try:
                            if isinstance(value, (list, tuple)):
                                attr = int(attr)
                            value = value[attr]
                        except Exception:
                            value = None

                    txt = safe_unicode(error).replace('for dictionary value', '')
                    txt = txt.strip()
                    if isinstance(error, RequiredFieldInvalid):
                        msg = '[{0}] {1}'
                    else:
                        msg = '[{0}] {1}: {2}'
                    try:
                        msg = msg.format(field, txt, str(value))
                    except Exception:
                        msg = '[{0}] {1}'.format(field, txt)

                else:
                    msg = str(error)
                errors.append(msg)
            msg = '\n- '.join(['Validation error:'] + errors)
            raise HarvestValidationError(msg)


class BaseSyncBackend(BaseBackend):
    """
    Parent class that wrap children methods to add error management and debug logs.

    The flow is the following:
        Parent                    Child

        harvest         ->    inner_harvest()
                                 /
        process_dataset  <------
                    \
                      --------> inner_process_dataset()

    """

    def inner_harvest(self):
        raise NotImplementedError
    
    def inner_process_dataset(self, dataset: Optional[Dataset]):
        raise NotImplementedError

    def harvest(self):
        log.debug(f'Starting harvesting {self.source.name} ({self.source.url})…')
        factory = HarvestJob if self.dryrun else HarvestJob.objects.create
        self.job = factory(status='initialized',
                           started=datetime.utcnow(),
                           source=self.source)

        before_harvest_job.send(self)

        try:
            self.inner_harvest()
            self.job.status = 'done'
        except HarvestValidationError as e:
            log.info(f'Harvesting validation failed for "{safe_unicode(self.source.name)}" ({self.source.backend})')

            self.job.status = 'failed'

            error = HarvestError(message=safe_unicode(e))
            self.job.errors.append(error)
        except Exception as e:
            log.exception(f'Harvesting failed for "{safe_unicode(self.source.name)}" ({self.source.backend})')

            self.job.status = 'failed'

            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            self.job.errors.append(error)
        finally:
            self.end_job()
        

    def process_dataset(self, remote_id: str, debug_data: dict, **kwargs):
        log.debug(f'Processing dataset {remote_id}…')

        # TODO add `type` to `HarvestItem` to differentiate `Dataset` from `Dataservice`
        item = HarvestItem(status='started', started=datetime.utcnow(), remote_id=remote_id, kwargs=debug_data)
        self.job.items.append(item)
        self.save_job()

        try:
            dataset = Dataset.objects(__raw__={
                'harvest.remote_id': remote_id,
                '$or': [
                    {'harvest.domain': self.source.domain},
                    {'harvest.source_id': str(self.source.id)},
                ],
            }).first()

            # TODO check that the existing dataset belongs to the same owner/organization than
            # the `HarvestSource`. Or is it always the case?

            if dataset is None:
                if self.source.organization:
                    dataset = Dataset(organization=self.source.organization)
                elif self.source.owner:
                    dataset = Dataset(owner=self.source.owner)
                else:
                    raise Exception(f"HarvestSource#{self.source.id} doesn't have an owner nor an organization")

            dataset = self.inner_process_dataset(dataset, **kwargs)

            if not dataset.harvest:
                dataset.harvest = HarvestDatasetMetadata()
            dataset.harvest.domain = self.source.domain
            dataset.harvest.remote_id = item.remote_id
            dataset.harvest.source_id = str(self.source.id)
            dataset.harvest.last_update = datetime.utcnow()
            dataset.harvest.backend = self.display_name

            # unset archived status if needed
            if dataset.harvest:
                dataset.harvest.archived_at = None
                dataset.harvest.archived = None
            dataset.archived = None

            # TODO: Apply editable mappings

            if self.dryrun:
                dataset.validate()
            else:
                dataset.save()
            item.dataset = dataset
            item.status = 'done'
        except HarvestSkipException as e:
            item.status = 'skipped'

            log.info(f'Skipped item {item.remote_id} : {safe_unicode(e)}')
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except HarvestValidationError as e:
            item.status = 'failed'

            log.info(f'Error validating item {item.remote_id} : {safe_unicode(e)}')
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except Exception as e:
            item.status = 'failed'
            log.exception(f'Error while processing {item.remote_id} : {safe_unicode(e)}')

            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            item.errors.append(error)
        finally:
            item.ended = datetime.utcnow()
            self.save_job()

    def save_job(self):
        if not self.dryrun:
            self.job.save()

    def end_job(self):
        self.job.ended = datetime.utcnow()
        if not self.dryrun:
            self.job.save()

        after_harvest_job.send(self)