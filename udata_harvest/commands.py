# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from . import actions

from udata.commands import submanager

log = logging.getLogger(__name__)

m = submanager('harvest',
    help='Remote repositories harvesting operations',
    description='Handle remote repositories harvesting operations'
)


@m.option('backend')
@m.option('url')
@m.option('name')
@m.option('-f', '--frequency', default=None)
@m.option('-u', '--owner', dest='owner', default=None)
@m.option('-o', '--org', dest='org', default=None)
def create(name, url, backend, frequency=None, owner=None, org=None):
    '''Create a new harvest source'''
    log.info('Creating a new Harvest source "%s"', name)
    source = actions.create_source(name, url, backend, frequency=frequency, owner=owner, org=org)
    log.info('''Created a new Harvest source:
    name: {0.name},
    slug: {0.slug},
    url: {0.url},
    backend: {0.backend},
    frequency: {0.frequency},
    owner: {0.owner},
    organization: {0.organization}'''.format(source))


@m.command
def delete(identifier):
    '''Delete an harvest source'''
    log.info('Deleting source "%s"', identifier)
    actions.delete_source(identifier)
    log.info('Deleted source "%s"', identifier)


@m.command
def sources():
    '''List all harvest sources'''
    sources = actions.list_sources()
    if sources:
        for source in sources:
            msg = '{0.name} ({0.backend}): {0.url}'
            log.info(msg.format(source))
    else:
        log.info('No sources defined yet')


@m.command
def backends():
    '''List available backends'''
    log.info('Available backends:')
    for name in actions.list_backends():
        log.info(name)


@m.command
def jobs():
    '''Lists started harvest jobs'''


@m.option('identifier', help='The Harvest source identifier or slug')
def launch(identifier):
    '''Launch a source harvesting on the workers'''
    log.info('Launching harvest job for source "%s"', identifier)
    actions.launch(identifier)


@m.option('identifier', help='The Harvest source identifier or slug')
@m.option('-d', '--debug', action='store_true', default=False, help='Debug/dry_run')
def run(identifier, debug=False):
    '''Run an harvester synchronously'''
    log.info('Harvest source "%s"', identifier)
    actions.run(identifier, debug=debug)



# @manager.option('name', help='Ini file name or harvester name')
# @manager.option('-o', '--organizations', action='store_true', default=False, help='Harvest organizations')
# @manager.option('-d', '--datasets', action='store_true', default=False, help='Harvest datasets')
# @manager.option('-r', '--reuses', action='store_true', default=False, help='Harvest reuses')
# @manager.option('-u', '--users', action='store_true', default=False, help='Harvest users')
# def harvest(name, organizations=False, users=False, datasets=False, reuses=False):
#     '''Launch harvesters'''
#     if exists(name):
#         harvester = Harvester.from_file(name)
#     else:
#         harvester = Harvester.objects.get(name=name)

#     backend = get_backend_for(harvester)
#     backend.harvest(organizations=organizations, datasets=datasets, reuses=reuses, users=users)
