# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

import click

from udata.commands import cli, exit_with_error, echo, white
from udata.tasks import schedulables, celery

from .models import PeriodicTask

log = logging.getLogger(__name__)

SCHEDULE_LINE = '{name}: {label} ↦ {schedule}'


def job_label(name, args, kwargs):
    label = name
    params = args[:]
    params += ['='.join((k, v)) for k, v in sorted(kwargs.items())]
    if params:
        label += '(' + ', '.join(params) + ')'
    return label


@cli.group('job')
def grp():
    '''Jobs related operations'''
    pass


@grp.command()
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
        exit_with_error('Job %s not found', name)
    job = celery.tasks[name]
    label = job_label(name, args, kwargs)
    if delay:
        log.info('Sending job %s', label)
        job.delay(*args, **kwargs)
        log.info('Job sended to workers')
    else:
        log.info('Running job %s', label)
        job.run(*args, **kwargs)
        log.info('Job %s done', name)


@grp.command()
def list():
    '''List all availables jobs'''
    for job in sorted([s.name for s in schedulables()]):
        echo(job)


@grp.command()
@click.argument('cron', metavar='<cron>')
@click.argument('name', metavar='<name>')
@click.argument('params', nargs=-1,  metavar='<arg key=value ...>')
def schedule(cron, name, params):
    '''
    Schedule the job <name> to run periodically given the <cron> expression.

    Jobs args and kwargs are given as parameters without dashes.

    Ex:
        udata job schedule "* * 0 * *" my-job arg1 arg2 key1=value key2=value
    '''
    if name not in celery.tasks:
        exit_with_error('Job %s not found', name)

    args = [p for p in params if '=' not in p]
    kwargs = dict(p.split('=') for p in params if '=' in p)
    label = 'Job {0}'.format(job_label(name, args, kwargs))

    try:
        task = PeriodicTask.objects.get(task=name, args=args, kwargs=kwargs)
        task.modify(crontab=PeriodicTask.Crontab.parse(cron))
    except PeriodicTask.DoesNotExist:
        task = PeriodicTask.objects.create(
            task=name,
            name=label,
            description='Periodic {0} job'.format(name),
            enabled=True,
            args=args,
            kwargs=kwargs,
            crontab=PeriodicTask.Crontab.parse(cron),
        )

    msg = 'Scheduled {label} with the following crontab: {cron}'
    log.info(msg.format(label=label, cron=task.schedule_display))


@grp.command()
@click.argument('name', metavar='<name>')
@click.argument('params', nargs=-1,  metavar='<arg key=value ...>')
def unschedule(name, params):
    '''
    Unschedule the job <name> with the given parameters.

    Jobs args and kwargs are given as parameters without dashes.

    Ex:
        udata job unschedule my-job arg1 arg2 key1=value key2=value
    '''
    if name not in celery.tasks:
        exit_with_error('Job %s not found', name)

    args = [p for p in params if '=' not in p]
    kwargs = dict(p.split('=') for p in params if '=' in p)
    label = 'Job {0}'.format(job_label(name, args, kwargs))

    try:
        task = PeriodicTask.objects.get(task=name, args=args, kwargs=kwargs)
    except PeriodicTask.DoesNotExist:
        exit_with_error('No scheduled job match {0}'.format(label))

    task.delete()
    msg = 'Unscheduled {label} with the following crontab: {cron}'
    log.info(msg.format(label=label, cron=task.schedule_display))


@grp.command()
def scheduled():
    '''
    List scheduled jobs.
    '''
    for job in sorted(schedulables(), key=lambda s: s.name):
        for task in PeriodicTask.objects(task=job.name):
            label = job_label(task.task, task.args, task.kwargs)
            echo(SCHEDULE_LINE.format(
                name=white(task.name.encode('utf8')),
                label=label,
                schedule=task.schedule_display
            ).encode('utf8'))
