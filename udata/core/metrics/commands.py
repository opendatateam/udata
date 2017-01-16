# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging


# from flask_script import Manager

from udata.commands import submanager
from udata.models import User, Dataset, Reuse, Organization

from . import metric_catalog
from .tasks import update_metrics_for, update_site_metrics

log = logging.getLogger(__name__)


m = submanager(
    'metrics',
    help='Metrics related operations',
    description='Handle all metrics related operations and maintenance'
)


def iter_catalog(*models):
    for model, metrics in metric_catalog.items():
        if not models or model.__name__.lower() in models:
            yield (model, metrics)


@m.option(
    '-s', '--site', action='store_true', default=False,
    help='Update site metrics')
@m.option(
    '-o', '--organizations', action='store_true', default=False,
    help='Compute organizations metrics')
@m.option(
    '-d', '--datasets', action='store_true', default=False,
    help='Compute datasets metrics')
@m.option(
    '-r', '--reuses', action='store_true', default=False,
    help='Compute reuses metrics')
@m.option(
    '-u', '--users', action='store_true', default=False,
    help='Compute users metrics')
def update(site=False, organizations=False, users=False, datasets=False,
           reuses=False):
    '''Update all metrics for the current date'''
    do_all = not any((site, organizations, users, datasets, reuses))

    if do_all or site:
        print 'Update site metrics'
        update_site_metrics()

    if do_all or datasets:
        print 'Update datasets metrics'
        for dataset in Dataset.objects.timeout(False):
            update_metrics_for(dataset)

    if do_all or reuses:
        print 'Update reuses metrics'
        for reuse in Reuse.objects.timeout(False):
            update_metrics_for(reuse)

    if do_all or organizations:
        print 'Update organizations metrics'
        for organization in Organization.objects.timeout(False):
            update_metrics_for(organization)

    if do_all or users:
        print 'Update user metrics'
        for user in User.objects.timeout(False):
            update_metrics_for(user)
