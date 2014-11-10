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


@m.command
def create():
    '''Create a new harvest source'''


@m.command
def delete():
    '''Delete an harvest source'''


@m.command
def sources():
    '''List all harvest sources'''
    sources = actions.list_sources()
    if sources:
        for source in sources:
            log.info(source)
    else:
        log.info('No sources defined yet')


@m.command
def jobs():
    '''Lists started harvest jobs'''





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
