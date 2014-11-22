# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.models import User, Organization

from . import backends
from .models import HarvestSource, DEFAULT_HARVEST_FREQUENCY
from .signals import harvest_source_created, harvest_source_deleted
from .tasks import harvest

log = logging.getLogger(__name__)


def list_backends():
    '''List all available backends'''
    return backends.get_all().keys()


def list_sources():
    '''List all harvest sources'''
    return list(HarvestSource.objects)


def get_source(ident):
    '''Get an harvest source given its ID or its slug'''
    return HarvestSource.get(ident)


def create_source(name, url, backend, frequency=DEFAULT_HARVEST_FREQUENCY, owner=None, org=None):
    '''Create a new harvest source'''
    if owner and not isinstance(owner, User):
        owner = User.get(owner)

    if org and not isinstance(org, Organization):
        org = Organization.get(org)

    source = HarvestSource.objects.create(
        name=name,
        url=url,
        backend=backend,
        frequency=frequency or DEFAULT_HARVEST_FREQUENCY,
        owner=owner,
        organization=org
    )
    harvest_source_created.send(source)
    return source


def delete_source(ident):
    '''Delete an harvest source'''
    source = get_source(ident)
    source.delete()
    harvest_source_deleted.send(source)
    # return source


def run(ident, debug=False):
    '''Launch or resume an harvesting for a given source if none is running'''
    source = get_source(ident)
    cls = backends.get(source.backend)
    backend = cls(source, debug=debug)
    backend.harvest()


def launch(ident, debug=False):
    '''Launch or resume an harvesting for a given source if none is running'''
    harvest.delay(ident)

