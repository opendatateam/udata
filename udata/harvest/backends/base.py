# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import traceback

from datetime import datetime, date
from uuid import UUID

import requests

from voluptuous import MultipleInvalid, RequiredFieldInvalid

from udata.models import Dataset
from udata.utils import safe_unicode

from ..exceptions import HarvestException, HarvestSkipException, HarvestValidationError
from ..models import HarvestItem, HarvestJob, HarvestError
from ..signals import before_harvest_job, after_harvest_job

log = logging.getLogger(__name__)

# Disable those annoying warnings
requests.packages.urllib3.disable_warnings()


class HarvestFilter(object):
    TYPES = {
        str: 'string',
        unicode: 'string',
        basestring: 'string',
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
        self.max_items = max_items

    @property
    def config(self):
        return self.source.config

    def get(self, url, **kwargs):
        headers = self.get_headers()
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def post(self, url, data, **kwargs):
        headers = self.get_headers()
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
                           started=datetime.now(),
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
            return
        except Exception as e:
            self.job.status = 'failed'
            error = HarvestError(message=safe_unicode(e))
            self.job.errors.append(error)
            self.end()
            msg = 'Initialization failed for "{0.name}" ({0.backend})'
            log.exception(msg.format(self.source))
            return

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
        item.started = datetime.now()
        if not self.dryrun:
            self.job.save()

        try:
            dataset = self.process(item)
            dataset.extras['harvest:source_id'] = str(self.source.id)
            dataset.extras['harvest:remote_id'] = item.remote_id
            dataset.extras['harvest:domain'] = self.source.domain
            dataset.extras['harvest:last_update'] = datetime.now().isoformat()

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
                dataset.last_modified = datetime.now()
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

        item.ended = datetime.now()
        if not self.dryrun:
            self.job.save()

    def process(self, item):
        raise NotImplementedError

    def add_item(self, identifier, *args, **kwargs):
        item = HarvestItem(remote_id=str(identifier), args=args, kwargs=kwargs)
        self.job.items.append(item)

    def finalize(self):
        self.job.status = 'done'
        if any(i.status == 'failed' for i in self.job.items):
            self.job.status += '-errors'
        self.end()

    def end(self):
        self.job.ended = datetime.now()
        if not self.dryrun:
            self.job.save()
        after_harvest_job.send(self)

    def get_dataset(self, remote_id):
        '''Get or create a dataset given its remote ID (and its source)
        We first try to match `source_id` to be source domain independent
        '''
        dataset = Dataset.objects(__raw__={
            'extras.harvest:remote_id': remote_id,
            '$or': [
                {'extras.harvest:domain': self.source.domain},
                {'extras.harvest:source_id': str(self.source.id)},
            ],
        }).first()
        return dataset or Dataset()

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
