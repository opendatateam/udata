# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

import requests

log = logging.getLogger(__name__)


class BaseBackend(object):
    name = None
    verify_ssl = True

    '''Base class for Harvester implementations'''
    def __init__(self, source, queue=None, debug=False):
        self.source = source
        self.queue = queue or []
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
        self.perform_initialization()
        self.iter_queue()

    def perform_initialization(self):
        '''Initialize the harvesting for a given job'''
        log.debug('Initializing backend')
        self.initialize()
        if self.queue:
            log.debug('Queued %s items', len(self.queue))

    def initialize(self, source, job):
        raise NotImplementedError

    def iter_queue(self):
        '''Process the data identified in the initialize stage'''
        while self.queue:
            url, args, kwargs = self.queue.pop(0)
            try:
                obj = self.process(url, *args, **kwargs)
                if self.debug:
                    obj.validate()
                else:
                    obj.save()
                log.debug('Processed %s', obj)
            except:
                log.exception('Unable to parse %s', url)

    def process(self, data, *args, **kwargs):
        raise NotImplementedError

    def enqueue(self, url, *args, **kwargs):
        self.queue.append((url, args, kwargs))
