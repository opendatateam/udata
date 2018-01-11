# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

import click

from udata.commands import cli, exit
from udata.tasks import schedulables, celery

log = logging.getLogger(__name__)


@cli.group()
def job():
    '''Jobs related operations'''
    pass


@job.command()
@click.argument('name', metavar='<name>')
@click.argument('params', nargs=-1,  metavar='<arg key=value ...>')
@click.option('-d', '--delay', is_flag=True,
          help='Run the job asynchronously on a worker')
def run(name, params, delay):
    '''
    Run the job <name>

    Jobs args and kwargs are given as parameters without dashes.

    Ex:
        udata job run my-job arg1 arg2 key1=value key2=value
        udata job run my-job -- arg1 arg2 key1=value key2=value
    '''
    args = [p for p in params if '=' not in p]
    kwargs = dict(p.split('=') for p in params if '=' in p)

    if name not in celery.tasks:
        exit('Job %s not found', name)
    job = celery.tasks[name]
    label = name
    if params:
        label += '(' + ', '.join(params) + ')'
    if delay:
        log.info('Sending job %s', label)
        job.delay(*args, **kwargs)
        log.info('Job sended to workers')
    else:
        log.info('Running job %s', label)
        job.run(*args, **kwargs)
        log.info('Job %s done', name)


@job.command()
def list():
    '''List all availables jobs'''
    for job in schedulables():
        log.info(job.name)
