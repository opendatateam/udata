# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

import requests

from ..models import HarvestItem

log = logging.getLogger(__name__)


class BaseHarvester(object):
    '''Base class for Harvester implementations'''
    #: A machine-readable name for configuration references.
    name = None
    #: A human-readable name for Web UI.
    title = None
    #: A short description.
    description = None
    verify_ssl = True

    def __init__(self, source):
        self.source = source

    @property
    def config(self):
        return self.source.config

    @property
    def job(self):
        return self.source.jobs[-1] if self.source.jobs else None

    def get(self, url, **kwargs):
        headers = self.get_headers()
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def get_headers(self):
        return {
            'User-Agent': 'uData/0.1 {0.name}'.format(self),  # TODO: extract site title and version
        }

    def harvest(self, async=False):
        '''Start the harvesting process'''
        self.handle_initialization()
        self.process_items()

    def handle_initialization(self):
        '''Initialize the harvesting for a given job'''
        log.debug('Initializing backend')
        self.initialize()
        if self.queue:
            log.debug('Queued %s items', len(self.queue))

    def process_items(self):
        '''Process the data identified in the initialize stage'''
        for item in self.job.items:
            try:
                obj = self.process(item)
                log.debug('Processed %s', obj)
                obj.validate()
            except:
                log.exception('Unable to parse %s', self.remote_url(item) or item)

    def add_item(self, remote_id):
        self.job.items.append(HarvestItem(remote_id=remote_id))

    def validate(self, config):
        '''
        An optionnal validation method for the configuration.

        It will be used on form validation and on each job start.
        It should raise Exceptions on error.
        '''

    def remote_url(self, item):
        '''
        Optionnaly provide a remote URL for an HarvestItem.

        :param item: an HarvestItem
        :returns: A string with the URL to the original document
        '''

    def initialize(self, job):
        '''
        This method is responsible for:
            - gathering all the necessary objects to fetch on a later.
              stage (e.g. for a CSW server, perform a GetRecords request)
            - creating the necessary HarvestItem. The HarvestItem need a
              reference date with the last modified date for the resource, this
              may need to be set in a different stage depending on the type of
              source.
            - creating and storing any suitable HarvestErrors that may occur.

        :param harvest_job: HarvestJob object
        :returns: A list of HarvestObject ids
        '''
        raise NotImplementedError

    def process(self, item):
        '''
        This method is responsible for:
            - getting the contents of the remote item.
            - creating or updating a local object
            - raising any HarvestError that may occur.
            - returning True if everything went as expected, False otherwise.

        :param item: HarvestItem object
        :returns: True if everything went right, False if errors were found
        '''
        raise NotImplementedError
