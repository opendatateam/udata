# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from argparse import SUPPRESS

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
    source = actions.create_source(name, url, backend,
                                   frequency=frequency,
                                   owner=owner,
                                   org=org)
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


@m.option('-s', '--scheduled', action='store_true', help='list only scheduled source')
def sources(scheduled=False):
    '''List all harvest sources'''
    sources = actions.list_sources()
    if scheduled:
        sources = [s for s in sources if s.periodic_task]
    if sources:
        for source in sources:
            msg = '{source.name} ({source.backend}): {cron}'
            cron = source.periodic_task.schedule_display if source.periodic_task else 'not scheduled'
            log.info(msg.format(source=source, cron=cron))
    elif scheduled:
        log.info('No sources scheduled yet')
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


@m.option('identifier', help='The Harvest source identifier or slug')
@m.option('-m', '--minute', help='The crontab expression for minute', default=SUPPRESS)
@m.option('-h', '--hour', help='The crontab expression for hour', default=SUPPRESS)
@m.option('-d', '--day', dest='day_of_week', help='The crontab expression for day of week', default=SUPPRESS)
@m.option('-D', '--day-of-month', dest='day_of_month', help='The crontab expression for day of month', default=SUPPRESS)
@m.option('-M', '--month-of-year', help='The crontab expression for month of year', default=SUPPRESS)
def schedule(identifier, **kwargs):
    log.info('Harvest source "%s"', identifier)
    source = actions.schedule(identifier, **kwargs)
    msg = 'Scheduled {source.name} with the following crontab: {cron}'
    log.info(msg.format(source=source, cron=source.periodic_task.crontab))


@m.option('identifier', help='The Harvest source identifier or slug')
def unschedule(identifier):
    '''Run an harvester synchronously'''
    source = actions.unschedule(identifier)
    log.info('Unscheduled harvest source "%s"', source.name)
