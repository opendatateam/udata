# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

from udata.commands import manager
from udata.core.user.factories import UserFactory, AdminFactory
from udata.core.dataset.factories import (DatasetFactory, VisibleDatasetFactory,
                                          DatasetDiscussionFactory)
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory

log = logging.getLogger(__name__)


def generate_users():
    user = UserFactory(email='user@udata', password='password')
    admin = AdminFactory(email='admin@udata', password='password')
    log.info('A new user with email "{0}" and password "password" was '
             'created.'.format(user.email))
    log.info('A new admin user with email "{0}" and password "password" was '
             'created.'.format(admin.email))


def generate_datasets():
    for _, i in enumerate(range(0, 10)):
        dataset = DatasetFactory() if i % 3 == 0 else VisibleDatasetFactory()
        DatasetDiscussionFactory(subject=dataset)
    log.info('10 new datasets were created.')


def generate_reuses():
    for _, i in enumerate(range(0, 10)):
        ReuseFactory() if i % 3 == 0 else VisibleReuseFactory()


@manager.command
def generate_fixtures():
    '''Build sample fixture data'''
    generate_users()
    generate_datasets()
    #generate_reuses()
