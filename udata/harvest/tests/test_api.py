# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import url_for

from .. import actions

from udata.models import Member, PeriodicTask
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.utils import faker
from udata.tests.helpers import assert200, assert201, assert204, assert403

from ..models import (
    HarvestSource, VALIDATION_ACCEPTED, VALIDATION_REFUSED, VALIDATION_PENDING,

)
from .factories import HarvestSourceFactory, MockBackendsMixin


log = logging.getLogger(__name__)


class HarvestAPITest(MockBackendsMixin):
    modules = ['core.organization', 'core.user', 'core.dataset']

    def test_list_backends(self, api):
        '''It should fetch the harvest backends list from the API'''
        response = api.get(url_for('api.harvest_backends'))
        assert200(response)
        assert len(response.json) == len(actions.list_backends())
        for data in response.json:
            assert 'id' in data
            assert 'label' in data

    def test_list_sources(self, api):
        sources = HarvestSourceFactory.create_batch(3)

        response = api.get(url_for('api.harvest_sources'))
        assert200(response)
        assert len(response.json['data']) == len(sources)

    def test_list_sources_for_owner(self, api):
        owner = UserFactory()
        sources = HarvestSourceFactory.create_batch(3, owner=owner)
        HarvestSourceFactory()

        url = url_for('api.harvest_sources', owner=str(owner.id))
        response = api.get(url)
        assert200(response)

        assert len(response.json['data']) == len(sources)

    def test_list_sources_for_org(self, api):
        org = OrganizationFactory()
        sources = HarvestSourceFactory.create_batch(3, organization=org)
        HarvestSourceFactory()

        response = api.get(url_for('api.harvest_sources', owner=str(org.id)))
        assert200(response)

        assert len(response.json['data']) == len(sources)

    def test_create_source_with_owner(self, api):
        '''It should create and attach a new source to an owner'''
        user = api.login()
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'factory'
        }
        response = api.post(url_for('api.harvest_sources'), data)

        assert201(response)

        source = response.json
        assert source['validation']['state'] == VALIDATION_PENDING
        assert source['owner']['id'] == str(user.id)
        assert source['organization'] is None

    def test_create_source_with_org(self, api):
        '''It should create and attach a new source to an organization'''
        user = api.login()
        member = Member(user=user, role='admin')
        org = OrganizationFactory(members=[member])
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'factory',
            'organization': str(org.id)
        }
        response = api.post(url_for('api.harvest_sources'), data)

        assert201(response)

        source = response.json
        assert source['validation']['state'] == VALIDATION_PENDING
        assert source['owner'] is None
        assert source['organization']['id'] == str(org.id)

    def test_create_source_with_org_not_member(self, api):
        '''It should create and attach a new source to an organization'''
        user = api.login()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'factory',
            'organization': str(org.id)
        }
        response = api.post(url_for('api.harvest_sources'), data)

        assert403(response)

    def test_update_source(self, api):
        '''It should update a source'''
        user = api.login()
        source = HarvestSourceFactory(owner=user)
        new_url = faker.url()
        data = {
            'name': source.name,
            'description': source.description,
            'url': new_url,
            'backend': 'factory',
        }
        api_url = url_for('api.harvest_source', ident=str(source.id))
        response = api.put(api_url, data)

        assert200(response)

        source = response.json
        assert source['url'] == new_url

    def test_validate_source(self, api):
        '''It should allow to validate a source if admin'''
        user = api.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {'state': VALIDATION_ACCEPTED}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = api.post(url, data)
        assert200(response)

        source.reload()
        assert source.validation.state == VALIDATION_ACCEPTED
        assert source.validation.by == user

    def test_reject_source(self, api):
        '''It should allow to reject a source if admin'''
        user = api.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {'state': VALIDATION_REFUSED, 'comment': 'Not valid'}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = api.post(url, data)
        assert200(response)

        source.reload()
        assert source.validation.state == VALIDATION_REFUSED
        assert source.validation.comment == 'Not valid'
        assert source.validation.by == user

    def test_validate_source_is_admin_only(self, api):
        '''It should allow to validate a source if admin'''
        api.login()
        source = HarvestSourceFactory()

        data = {'validate': True}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = api.post(url, data)
        assert403(response)

    def test_get_source(self, api):
        source = HarvestSourceFactory()

        url = url_for('api.harvest_source', ident=str(source.id))
        response = api.get(url)
        assert200(response)

    def test_source_preview(self, api):
        source = HarvestSourceFactory(backend='factory')

        url = url_for('api.preview_harvest_source', ident=str(source.id))
        response = api.get(url)
        assert200(response)

    def test_delete_source(self, api):
        user = api.login()
        source = HarvestSourceFactory(owner=user)

        url = url_for('api.harvest_source', ident=str(source.id))
        response = api.delete(url)
        assert204(response)

        deleted_sources = HarvestSource.objects(deleted__exists=True)
        assert len(deleted_sources) == 1

    def test_schedule_source(self, api):
        '''It should allow to schedule a source if admin'''
        api.login(AdminFactory())
        source = HarvestSourceFactory()

        data = '0 0 * * *'
        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = api.post(url, data)
        assert200(response)

        assert response.json['schedule'] == '0 0 * * *'

        source.reload()
        assert source.periodic_task is not None
        periodic_task = source.periodic_task
        assert periodic_task.crontab.hour == '0'
        assert periodic_task.crontab.minute == '0'
        assert periodic_task.crontab.day_of_week == '*'
        assert periodic_task.crontab.day_of_month == '*'
        assert periodic_task.crontab.month_of_year == '*'
        assert periodic_task.enabled

    def test_schedule_source_is_admin_only(self, api):
        '''It should only allow admins to schedule a source'''
        api.login()
        source = HarvestSourceFactory()

        data = '0 0 * * *'
        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = api.post(url, data)
        assert403(response)

        source.reload()
        assert source.periodic_task is None

    def test_unschedule_source(self, api):
        '''It should allow to unschedule a source if admin'''
        api.login(AdminFactory())
        periodic_task = PeriodicTask.objects.create(
            task='harvest',
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab()
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = api.delete(url)
        assert204(response)

        source.reload()
        assert source.periodic_task is None

    def test_unschedule_source_is_admin_only(self, api):
        '''It should only allow admins to unschedule a source'''
        api.login()
        periodic_task = PeriodicTask.objects.create(
            task='harvest',
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab()
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = api.delete(url)
        assert403(response)

        source.reload()
        assert source.periodic_task is not None
