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
                                   organization=org)
    log.info('''Created a new Harvest source:
    name: {0.name},
    slug: {0.slug},
    url: {0.url},
    backend: {0.backend},
    frequency: {0.frequency},
    owner: {0.owner},
    organization: {0.organization}'''.format(source))


@m.option('identifier')
def validate(identifier):
    '''Validate a source given its identifier'''
    source = actions.validate_source(identifier)
    log.info('Source %s (%s) has been validated', source.slug, str(source.id))


@m.command
def delete(identifier):
    '''Delete an harvest source'''
    log.info('Deleting source "%s"', identifier)
    actions.delete_source(identifier)
    log.info('Deleted source "%s"', identifier)


@m.option('-s', '--scheduled',
          action='store_true',
          help='list only scheduled source')
def sources(scheduled=False):
    '''List all harvest sources'''
    sources = actions.list_sources()
    if scheduled:
        sources = [s for s in sources if s.periodic_task]
    if sources:
        for source in sources:
            msg = '{source.name} ({source.backend}): {cron}'
            if source.periodic_task:
                cron = source.periodic_task.schedule_display
            else:
                cron = 'not scheduled'
            log.info(msg.format(source=source, cron=cron))
    elif scheduled:
        log.info('No sources scheduled yet')
    else:
        log.info('No sources defined yet')


@m.command
def backends():
    '''List available backends'''
    log.info('Available backends:')
    for backend in actions.list_backends():
        log.info('%s (%s)', backend.name, backend.display_name or backend.name)


@m.command
def jobs():
    '''Lists started harvest jobs'''


@m.option('identifier', help='The Harvest source identifier or slug')
def launch(identifier):
    '''Launch a source harvesting on the workers'''
    log.info('Launching harvest job for source "%s"', identifier)
    actions.launch(identifier)


@m.option('identifier', help='The Harvest source identifier or slug')
def run(identifier):
    '''Run an harvester synchronously'''
    log.info('Harvest source "%s"', identifier)
    actions.run(identifier)


@m.option('identifier', help='The Harvest source identifier or slug')
@m.option('-m', '--minute', default=SUPPRESS,
          help='The crontab expression for minute')
@m.option('-h', '--hour', default=SUPPRESS,
          help='The crontab expression for hour')
@m.option('-d', '--day', dest='day_of_week', default=SUPPRESS,
          help='The crontab expression for day of week')
@m.option('-D', '--day-of-month', dest='day_of_month', default=SUPPRESS,
          help='The crontab expression for day of month')
@m.option('-M', '--month-of-year', default=SUPPRESS,
          help='The crontab expression for month of year')
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


@m.command
def purge():
    '''Permanently remove deleted harvest sources'''
    log.info('Purging deleted harvest sources')
    count = actions.purge_sources()
    log.info('Purged %s source(s)', count)


@m.option('filename', help='The mapping CSV filename')
@m.option('domain', help='The remote domain')
def attach(domain, filename):
    '''Attach existing dataset to their harvest remote id.'''
    log.info('Attaching datasets for domain %s', domain)
    result = actions.attach(domain, filename)
    log.info('Attached %s datasets to %s', result.success, domain)
