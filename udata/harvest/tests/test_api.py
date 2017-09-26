# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import url_for

from .. import actions

from udata.models import Member, PeriodicTask
from udata.tests.api import APITestCase
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.utils import faker

from ..models import (
    HarvestSource, VALIDATION_ACCEPTED, VALIDATION_REFUSED, VALIDATION_PENDING,

)
from .factories import HarvestSourceFactory, MockBackendsMixin


log = logging.getLogger(__name__)


class HarvestAPITest(MockBackendsMixin, APITestCase):
    modules = ['core.organization', 'core.user', 'core.dataset']

    def test_list_backends(self):
        '''It should fetch the harvest backends list from the API'''
        response = self.get(url_for('api.harvest_backends'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(actions.list_backends()))
        for data in response.json:
            self.assertIn('id', data)
            self.assertIn('label', data)

    def test_list_sources(self):
        sources = HarvestSourceFactory.create_batch(3)

        response = self.get(url_for('api.harvest_sources'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(sources))

    def test_list_sources_for_owner(self):
        owner = UserFactory()
        sources = HarvestSourceFactory.create_batch(3, owner=owner)
        HarvestSourceFactory()

        url = url_for('api.harvest_sources', owner=str(owner.id))
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(sources))

    def test_list_sources_for_org(self):
        org = OrganizationFactory()
        sources = HarvestSourceFactory.create_batch(3, organization=org)
        HarvestSourceFactory()

        response = self.get(url_for('api.harvest_sources', owner=str(org.id)))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(sources))

    def test_create_source_with_owner(self):
        '''It should create and attach a new source to an owner'''
        user = self.login()
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'factory'
        }
        response = self.post(url_for('api.harvest_sources'), data)

        self.assert201(response)

        source = response.json
        self.assertEqual(source['validation']['state'], VALIDATION_PENDING)
        self.assertEqual(source['owner']['id'], str(user.id))
        self.assertIsNone(source['organization'])

    def test_create_source_with_org(self):
        '''It should create and attach a new source to an organization'''
        user = self.login()
        member = Member(user=user, role='admin')
        org = OrganizationFactory(members=[member])
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'factory',
            'organization': str(org.id)
        }
        response = self.post(url_for('api.harvest_sources'), data)

        self.assert201(response)

        source = response.json
        self.assertEqual(source['validation']['state'], VALIDATION_PENDING)
        self.assertIsNone(source['owner'])
        self.assertEqual(source['organization']['id'], str(org.id))

    def test_create_source_with_org_not_member(self):
        '''It should create and attach a new source to an organization'''
        user = self.login()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'factory',
            'organization': str(org.id)
        }
        response = self.post(url_for('api.harvest_sources'), data)

        self.assert403(response)

    def test_update_source(self):
        '''It should update a source'''
        user = self.login()
        source = HarvestSourceFactory(owner=user)
        new_url = faker.url()
        data = {
            'name': source.name,
            'description': source.description,
            'url': new_url,
            'backend': 'factory',
        }
        api_url = url_for('api.harvest_source', ident=str(source.id))
        response = self.put(api_url, data)

        self.assert200(response)

        source = response.json
        self.assertEqual(source['url'], new_url)

    def test_validate_source(self):
        '''It should allow to validate a source if admin'''
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {'state': VALIDATION_ACCEPTED}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert200(response)

        source.reload()
        self.assertEqual(source.validation.state, VALIDATION_ACCEPTED)
        self.assertEqual(source.validation.by, self.user)

    def test_reject_source(self):
        '''It should allow to reject a source if admin'''
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {'state': VALIDATION_REFUSED, 'comment': 'Not valid'}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert200(response)

        source.reload()
        self.assertEqual(source.validation.state, VALIDATION_REFUSED)
        self.assertEqual(source.validation.comment, 'Not valid')
        self.assertEqual(source.validation.by, self.user)

    def test_validate_source_is_admin_only(self):
        '''It should allow to validate a source if admin'''
        self.login()
        source = HarvestSourceFactory()

        data = {'validate': True}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert403(response)

    def test_get_source(self):
        source = HarvestSourceFactory()

        url = url_for('api.harvest_source', ident=str(source.id))
        response = self.get(url)
        self.assert200(response)

    def test_source_preview(self):
        source = HarvestSourceFactory(backend='factory')

        url = url_for('api.preview_harvest_source', ident=str(source.id))
        response = self.get(url)
        self.assert200(response)

    def test_delete_source(self):
        user = self.login()
        source = HarvestSourceFactory(owner=user)

        url = url_for('api.harvest_source', ident=str(source.id))
        response = self.delete(url)
        self.assert204(response)

        deleted_sources = HarvestSource.objects(deleted__exists=True)
        self.assertEqual(len(deleted_sources), 1)

    def test_schedule_source(self):
        '''It should allow to schedule a source if admin'''
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = '0 0 * * *'
        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert200(response)

        self.assertEqual(response.json['schedule'], '0 0 * * *')

        source.reload()
        self.assertIsNotNone(source.periodic_task)
        periodic_task = source.periodic_task
        self.assertEqual(periodic_task.crontab.hour, '0')
        self.assertEqual(periodic_task.crontab.minute, '0')
        self.assertEqual(periodic_task.crontab.day_of_week, '*')
        self.assertEqual(periodic_task.crontab.day_of_month, '*')
        self.assertEqual(periodic_task.crontab.month_of_year, '*')
        self.assertTrue(periodic_task.enabled)

    def test_schedule_source_is_admin_only(self):
        '''It should only allow admins to schedule a source'''
        self.login()
        source = HarvestSourceFactory()

        data = '0 0 * * *'
        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert403(response)

        source.reload()
        self.assertIsNone(source.periodic_task)

    def test_unschedule_source(self):
        '''It should allow to unschedule a source if admin'''
        self.login(AdminFactory())
        periodic_task = PeriodicTask.objects.create(
            task='harvest',
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab()
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = self.delete(url)
        self.assert204(response)

        source.reload()
        self.assertIsNone(source.periodic_task)

    def test_unschedule_source_is_admin_only(self):
        '''It should only allow admins to unschedule a source'''
        self.login()
        periodic_task = PeriodicTask.objects.create(
            task='harvest',
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab()
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for('api.schedule_harvest_source', ident=str(source.id))
        response = self.delete(url)
        self.assert403(response)

        source.reload()
        self.assertIsNotNone(source.periodic_task)
