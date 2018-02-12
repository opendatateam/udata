# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import click

from udata.commands import cli, success, echo, white
from udata.models import User, Dataset, Reuse, Organization

from . import metric_catalog
from .tasks import update_metrics_for, update_site_metrics

log = logging.getLogger(__name__)


@cli.group('metrics')
def grp():
    '''Metrics related operations'''
    pass


def iter_catalog(*models):
    for model, metrics in metric_catalog.items():
        if not models or model.__name__.lower() in models:
            yield (model, metrics)


@grp.command()
@click.option('-s', '--site', is_flag=True, help='Update site metrics')
@click.option('-o', '--organizations', is_flag=True,
              help='Compute organizations metrics')
@click.option('-d', '--datasets', is_flag=True,
              help='Compute datasets metrics')
@click.option('-r', '--reuses', is_flag=True, help='Compute reuses metrics')
@click.option('-u', '--users', is_flag=True, help='Compute users metrics')
def update(site=False, organizations=False, users=False, datasets=False,
           reuses=False):
    '''Update all metrics for the current date'''
    do_all = not any((site, organizations, users, datasets, reuses))

    if do_all or site:
        log.info('Update site metrics')
        update_site_metrics()

    if do_all or datasets:
        log.info('Update datasets metrics')
        for dataset in Dataset.objects.timeout(False):
            update_metrics_for(dataset)

    if do_all or reuses:
        log.info('Update reuses metrics')
        for reuse in Reuse.objects.timeout(False):
            update_metrics_for(reuse)

    if do_all or organizations:
        log.info('Update organizations metrics')
        for organization in Organization.objects.timeout(False):
            update_metrics_for(organization)

    if do_all or users:
        log.info('Update user metrics')
        for user in User.objects.timeout(False):
            update_metrics_for(user)

    success('All metrics have been updated')


@grp.command()
def list():
    '''List all known metrics'''
    for cls, metrics in metric_catalog.items():
        echo(white(cls.__name__))

        for metric in metrics.keys():
            echo('> {0}'.format(metric))
