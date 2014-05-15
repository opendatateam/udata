# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging


from udata.commands import manager
from udata.models import User, Dataset, Reuse, Organization

from .tasks import update_metrics_for, update_site_metrics

log = logging.getLogger(__name__)


@manager.option('-s', '--site', action='store_true', default=False, help='Update site metrics')
@manager.option('-o', '--organizations', action='store_true', default=False, help='Compute organizations metrics')
@manager.option('-d', '--datasets', action='store_true', default=False, help='Compute datasets metrics')
@manager.option('-r', '--reuses', action='store_true', default=False, help='Compute reuses metrics')
@manager.option('-u', '--users', action='store_true', default=False, help='Compute users metrics')
def update_metrics(site=False, organizations=False, users=False, datasets=False, reuses=False):
    do_all = not any((site, organizations, users, datasets, reuses))

    if do_all or site:
        print 'Update site metrics'
        update_site_metrics()

    if do_all or datasets:
        print 'Update datasets metrics'
        for dataset in Dataset.objects:
            update_metrics_for(dataset)

    if do_all or reuses:
        print 'Update reuses metrics'
        for reuse in Reuse.objects:
            update_metrics_for(reuse)

    if do_all or organizations:
        print 'Update organizations metrics'
        for organization in Organization.objects:
            update_metrics_for(organization)

    if do_all or users:
        print 'Update user metrics'
        for user in User.objects:
            update_metrics_for(user)
