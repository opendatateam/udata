# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import manager
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory

log = logging.getLogger(__name__)


@manager.command
def generate_fixtures(datasets=5, reuses=1):
    '''Build sample fixture data (users, datasets and reuses).'''
    user = UserFactory()
    log.info('Generated user "{user.email}".'.format(user=user))

    organization = OrganizationFactory(members=[Member(user=user)])
    log.info('Generated organization "{org.name}".'.format(org=organization))

    for _ in range(datasets):
        dataset = VisibleDatasetFactory(organization=organization)
        DiscussionFactory(subject=dataset, user=user)
        ReuseFactory.create_batch(reuses, datasets=[dataset], owner=user)

    msg = 'Generated {datasets} dataset(s) with {reuses} reuse(s) each.'
    log.info(msg.format(**locals()))
