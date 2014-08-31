# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

from datetime import datetime
from sys import stdout, stderr


log = logging.getLogger(__name__)

from flask import current_app
from flask.ext.security import login_user, current_user

from udata.models import User

from ..models import HarvestReference

LOG_EACH = 50


class BaseBackend(object):
    '''Base class for Harvester implementations'''
    def __init__(self, harvester):
        self.harvester = harvester

    @property
    def config(self):
        return self.harvester.config

    def harvest(self, organizations=False, users=False, datasets=False, reuses=False):
        user_id = self.config.get('user')
        self.user = User.objects.get(id=user_id)
        login_user(self.user)
        do_all = not any((organizations, users, datasets, reuses))
        self.initialize()
        if do_all or users:
            self.harvest_users()
        if do_all or organizations:
            self.harvest_organizations()
        if do_all or datasets:
            self.harvest_datasets()
        if do_all or reuses:
            self.harvest_reuses()
        self.finalize()

    def initialize(self):
        current_app.logger.debug('Backend initialization')

    def stdout(self, message):
        stdout.write(str(message))
        stdout.flush()

    def stderr(self, message):
        stderr.write(str(message))
        stderr.flush()

    def harvest_organizations(self):
        self.stdout('Harvesting organizations\n')
        for idx, organization in enumerate(self.remote_organizations(), 1):
            try:
                organization.save()
            except Exception as e:
                current_app.logger.error('Unable to save organization %s: %s', organization.name, e)
                # log.error('Unable to save organization %s: %s', organization.name, e)
            self.stdout('.' if idx % LOG_EACH else idx)
        self.stdout('\n')

    def remote_organizations(self):
        log.debug('Remote organizations not implemented')
        return tuple()

    def harvest_datasets(self):
        self.stdout('Harvesting datasets\n')
        for idx, dataset in enumerate(self.remote_datasets()):
            try:
                dataset.save()
            except Exception as e:
                current_app.logger.error('Unable to save dataset %s: %s', dataset.title, e)
            self.stdout('.' if idx % LOG_EACH else idx)
        self.stdout('\n')

    def remote_datasets(self):
        log.debug('Remote datasets not implemented')
        return tuple()

    def harvest_reuses(self):
        self.stdout('Harvesting reuses\n')
        for idx, reuse in enumerate(self.remote_reuses()):
            try:
                reuse.save()
            except Exception as e:
                current_app.logger.error('Unable to save reuse %s: %s', reuse.title, e)
            self.stdout('.' if idx % LOG_EACH else idx)
        self.stdout('\n')

    def remote_reuses(self):
        log.debug('Remote reuses not implemented')
        return tuple()

    def harvest_users(self):
        self.stdout('Harvesting users\n')
        for idx, user in enumerate(self.remote_users()):
            try:
                user.save()
            except Exception as e:
                current_app.logger.error('Unable to save user %s: %s', user.fullname, e)
            self.stdout('.' if idx % LOG_EACH else idx)
        self.stdout('\n')

    def remote_users(self):
        log.debug('Remote users not implemented')
        return tuple()

    def finalize(self):
        current_app.logger.debug('Backend Finalization')

    def harvested_qs(self, model, **kwargs):
        return model.objects(ext__harvest__harvester=self.harvester.id, **kwargs)

    def get_harvested(self, model, remote_id, create=True, **kwargs):
        obj, created = self.harvested_qs(model, **kwargs).get_or_create(auto_save=False,
                                                        ext__harvest__remote_id=remote_id)
        if created and not create:
            return None

        obj.ext['harvest'] = HarvestReference(
            remote_id=remote_id,
            harvester=self.harvester,
            last_update=datetime.now()
        )
        return obj

    def map(self, field, dict_or_obj, default=None):
        if isinstance(dict_or_obj, dict):
            value = dict_or_obj.get(field, default)
        else:
            value = getattr(dict_or_obj, field, default)
        if field not in self.harvester.mapping:
            return value
        return self.harvester.mapping[field].get(value, default)


def get_backend_for(harvester):
    if harvester.backend == 'ckan':
        from .ckan import CkanBackend
        return CkanBackend(harvester)
    else:
        raise ValueError('Unkown backend "{0}"'.format(harvester.backend))
