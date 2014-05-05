# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from flask import url_for

from udata.models import User

from . import APITestCase
from ..factories import DatasetFactory, OrganizationFactory, ReuseFactory


class MeAPITest(APITestCase):
    def test_get_profile(self):
        '''It should fetch my user data on GET'''
        self.login()
        response = self.get(url_for('api.me'))
        self.assert200(response)
        self.assertEqual(response.json['email'], self.user.email)

    def test_update_profile(self):
        '''It should update a dataset from the API'''
        self.login()
        data = self.user.to_dict()
        data['about'] = 'new about'
        response = self.put(url_for('api.me'), data)
        self.assert200(response)
        self.assertEqual(User.objects.count(), 1)
        self.user.reload()
        self.assertEqual(self.user.about, 'new about')

    def test_star_dataset(self):
        '''It should mark the dataset starred on POST'''
        user = self.login()
        dataset = DatasetFactory()

        response = self.post(url_for('api.starred_datasets', slug=dataset.slug))
        self.assertStatus(response, 201)

        user.reload()
        self.assertIn(dataset, user.starred_datasets)

    def test_star_dataset_already_starred(self):
        '''It shouldn't do anything when featuring an already featured dataset'''
        user = self.login()
        dataset = DatasetFactory()

        user.starred_datasets.append(dataset)
        user.save()

        response = self.post(url_for('api.starred_datasets', slug=dataset.slug))
        self.assert200(response)

        user.reload()
        self.assertIn(dataset, user.starred_datasets)

    def test_unstar_dataset(self):
        '''It should unstar the dataset on DELETE'''
        user = self.login()
        dataset = DatasetFactory()

        user.starred_datasets.append(dataset)
        user.save()

        response = self.delete(url_for('api.starred_datasets', slug=dataset.slug))
        self.assertStatus(response, 204)

        user.reload()
        self.assertNotIn(dataset, user.starred_datasets)

    def test_star_reuse(self):
        '''It should star a reuse on POST'''
        user = self.login()
        reuse = ReuseFactory()

        response = self.post(url_for('api.starred_reuses', slug=reuse.slug))
        self.assertStatus(response, 201)

        user.reload()
        self.assertIn(reuse, user.starred_reuses)

    def test_star_reuse_already_starred(self):
        '''It shouldn't do anything when starring an already starred reuse'''
        user = self.login()
        reuse = ReuseFactory()

        user.starred_reuses.append(reuse)
        user.save()

        response = self.post(url_for('api.starred_reuses', slug=reuse.slug))
        self.assert200(response)

        user.reload()
        self.assertIn(reuse, user.starred_reuses)

    def test_unstar_reuse(self):
        '''It should unstar reuse on DELETE'''
        user = self.login()
        reuse = ReuseFactory()

        user.starred_reuses.append(reuse)
        user.save()

        response = self.delete(url_for('api.starred_reuses', slug=reuse.slug))
        self.assertStatus(response, 204)

        user.reload()
        self.assertNotIn(reuse, user.starred_reuses)

    def test_star_organization(self):
        '''It should star a organization on POST'''
        user = self.login()
        organization = OrganizationFactory()

        response = self.post(url_for('api.starred_organizations', slug=organization.slug))
        self.assertStatus(response, 201)

        user.reload()
        self.assertIn(organization, user.starred_organizations)

    def test_star_organization_already_starred(self):
        '''It shouldn't do anything when starring an already starred organization'''
        user = self.login()
        organization = OrganizationFactory()

        user.starred_organizations.append(organization)
        user.save()

        response = self.post(url_for('api.starred_organizations', slug=organization.slug))
        self.assert200(response)

        user.reload()
        self.assertIn(organization, user.starred_organizations)

    def test_unstar_organization(self):
        '''It should unstar organization on DELETE'''
        user = self.login()
        organization = OrganizationFactory()

        user.starred_organizations.append(organization)
        user.save()

        response = self.delete(url_for('api.starred_organizations', slug=organization.slug))
        self.assertStatus(response, 204)

        user.reload()
        self.assertNotIn(organization, user.starred_organizations)
