# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
import logging

from udata.commands import manager
from udata.core.dataset.factories import VisibleDatasetFactory, LicenseFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory, TeamFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.user.factories import AdminFactory

log = logging.getLogger(__name__)


def generate_datasets(count, organization=None):
    for _ in range(0, count):
        dataset = VisibleDatasetFactory(organization=organization)
        DiscussionFactory(subject=dataset)


def generate_reuses(count, user=None):
    VisibleReuseFactory.create_batch(count, owner=user)


def generate_licenses(count):
    for _ in range(0, count):
        LicenseFactory()


@manager.command
def generate_fixtures():
    '''Build sample fixture data (users, datasets and reuses).'''
    user = AdminFactory(email='user@udata', password='password',
                        confirmed_at=datetime.now())
    log.info('Generated admin user "user@udata" with password "password".')

    team = TeamFactory(members=[user])
    organization = OrganizationFactory(teams=[team])
    log.info('A team and an organization were generated for "user@udata".')

    generate_datasets(count=5, organization=organization)
    generate_reuses(count=5)
    log.info('10 new datasets 5 reuses were generated.')

    generate_licenses(count=2)
    log.info('2 new licences were generated.')
