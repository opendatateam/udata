# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Organization

from . import APITestCase
from ..factories import OrganizationFactory


class OrganizationAPITest(APITestCase):
    def test_organization_api_list(self):
        '''It should fetch an organization list from the API'''
        with self.autoindex():
            organizations = [OrganizationFactory() for i in range(3)]

        response = self.get(url_for('api.organizations'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(organizations))

    # def test_organization_api_get_not_found(self):
    #     '''It should raise 404 on API fetch if not found'''
    #     response = self.w.get(url_for('api.organization', slug='not-found'))
    #     self.assertEqual(response.status_code, 404)

    def test_organization_api_get(self):
        '''It should fetch an organization from the API'''
        organization = OrganizationFactory()
        response = self.get(url_for('api.organization', slug=organization.slug))
        self.assert200(response)

    def test_organization_api_create(self):
        '''It should create an organization from the API'''
        data = OrganizationFactory.attributes()
        self.login()
        response = self.post(url_for('api.organizations'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Organization.objects.count(), 1)

    def test_dataset_api_update(self):
        '''It should update an organization from the API'''
        org = OrganizationFactory()
        data = org.to_dict()
        data['description'] = 'new description'
        self.login()
        response = self.put(url_for('api.organization', slug=org.slug), data)
        self.assert200(response)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Organization.objects.first().description, 'new description')

    def test_organization_api_delete(self):
        '''It should delete an organization from the API'''
        organization = OrganizationFactory()
        response = self.delete(url_for('api.organization', slug=organization.slug))
        self.assertStatus(response, 204)
        self.assertEqual(Organization.objects.count(), 0)

    # def test_organization_api_delete_not_found(self):
    #     '''It should raise a 404 on delete from the API if not found'''
    #     OrganizationFactory()
    #     response = self.w.delete(url_for('api.organization', slug='not-found'))
    #     self.assertEqual(response.status_code, 404)
    #     self.assertEqual(Organization.objects.count(), 1)
