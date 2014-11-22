# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import traceback

from datetime import datetime

import requests

from ..models import HarvestItem, HarvestJob, HarvestError
from ..signals import before_harvest_job, after_harvest_job

log = logging.getLogger(__name__)


class BaseBackend(object):
    name = None
    verify_ssl = True

    '''Base class for Harvester implementations'''
    def __init__(self, source, job=None, debug=False):
        self.source = source
        self.job = job
        self.debug = debug

    @property
    def config(self):
        return self.source.config

    def get(self, url, **kwargs):
        headers = self.get_headers()
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def get_headers(self):
        return {
            'User-Agent': 'uData/0.1 {0.name}'.format(self),  # TODO: extract site title and version
        }

    def harvest(self):
        '''Start the harvesting process'''
        if self.perform_initialization():
            self.process_items()
            self.finalize()

    def perform_initialization(self):
        '''Initialize the harvesting for a given job'''
        log.debug('Initializing backend')
        self.job = HarvestJob.objects.create(status='initializing', started=datetime.now())
        self.source.jobs.append(self.job)
        self.source.save()

        before_harvest_job.send(self)

        try:
            self.initialize()
            self.job.status = 'initialized'
            self.job.save()
        except Exception as e:
            self.job.status = 'failed'
            error = HarvestError(message=str(e))
            self.job.errors.append(error)
            self.end()
            return

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
        self.job.save()

        try:
            obj = self.process(item)
            if self.debug:
                obj.validate()
            else:
                obj.save()
            item.status = 'done'
        except Exception as e:
            error = HarvestError(message=str(e), details=traceback.format_exc())
            item.errors.append(error)
            item.status = 'failed'

        item.ended = datetime.now()
        self.job.save()

    def process(self, item):
        raise NotImplementedError

    def add_item(self, identifier, *args, **kwargs):
        item = HarvestItem(remote_id=str(identifier), args=args, kwargs=kwargs)
        self.job.items.append(item)

    def finalize(self):
        self.job.status = 'done'
        if any(i.errors for i in self.job.items):
            self.job.status += '-errors'
        self.end()

    def end(self):
        self.job.ended = datetime.now()
        self.job.save()
        after_harvest_job.send(self)
