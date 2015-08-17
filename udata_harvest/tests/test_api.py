# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import url_for

from .. import actions

from udata.models import Member
from udata.settings import Testing
from udata.tests.api import APITestCase
from udata.tests.factories import faker, OrganizationFactory, AdminFactory

from .factories import HarvestSourceFactory

from .factories import (
    HarvestSourceFactory, DEFAULT_COUNT as COUNT
)


log = logging.getLogger(__name__)


class HarvestSettings(Testing):
    TEST_WITH_PLUGINS = True
    PLUGINS = ['harvest']


class HarvestAPITest(APITestCase):
    settings = HarvestSettings

    def test_list_backends(self):
        '''It should fetch the harvest backends list from the API'''
        response = self.get(url_for('api.harvest_backends'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(actions.list_backends()))
        for data in response.json:
            self.assertIn('id', data)
            self.assertIn('label', data)

    def test_create_source_with_owner(self):
        '''It should create and attach a new source to an owner'''
        user = self.login()
        data = {
            'name': faker.word(),
            'url': faker.url(),
            'backend': 'dummy'
        }
        response = self.post(url_for('api.harvest_sources'), data)

        self.assert201(response)

        source = response.json
        self.assertFalse(source['validated'])
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
            'backend': 'dummy',
            'organization': str(org.id)
        }
        response = self.post(url_for('api.harvest_sources'), data)

        self.assert201(response)

        source = response.json
        self.assertFalse(source['validated'])
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
            'backend': 'dummy',
            'organization': str(org.id)
        }
        response = self.post(url_for('api.harvest_sources'), data)

        self.assert403(response)

    def test_validate_source(self):
        '''It should allow to validate a source if admin'''
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {'validate': True}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert200(response)

        source.reload()
        self.assertTrue(source.validated)

    def test_reject_source(self):
        '''It should allow to reject a source if admin'''
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {'validate': False, 'comment': 'Not valid'}
        url = url_for('api.validate_harvest_source', ident=str(source.id))
        response = self.post(url, data)
        self.assert200(response)

        source.reload()
        self.assertFalse(source.validated)
        self.assertEqual(source.validation_comment, 'Not valid')

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
