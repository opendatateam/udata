# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging


from udata.commands import manager
from udata.models import User, Dataset, Reuse, Organization

from .tasks import update_metrics_for, update_site_metrics

log = logging.getLogger(__name__)


@manager.command
def update_metrics():
    print 'Update site metrics'
    update_site_metrics()
    print 'Update datasets metrics'
    for dataset in Dataset.objects:
        update_metrics_for(dataset)
    print 'Update reuses metrics'
    for reuse in Reuse.objects:
        update_metrics_for(reuse)
    print 'Update organizations metrics'
    for organization in Organization.objects:
        update_metrics_for(organization)
    print 'Update user metrics'
    for user in User.objects:
        update_metrics_for(user)
