# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Dataset

from .. import TestCase, DBTestMixin
from ..factories import (
    ResourceFactory, DatasetFactory, UserFactory, OrganizationFactory
)


class DatasetModelTest(TestCase, DBTestMixin):
    def test_owned_by_user(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        DatasetFactory(owner=UserFactory())

        result = Dataset.objects.owned_by(user)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], dataset)

    def test_owned_by_org(self):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        DatasetFactory(organization=OrganizationFactory())

        result = Dataset.objects.owned_by(org)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], dataset)

    def test_owned_by_org_or_user(self):
        user = UserFactory()
        org = OrganizationFactory()
        datasets = [DatasetFactory(owner=user),
                    DatasetFactory(organization=org)]
        excluded = [DatasetFactory(owner=UserFactory()),
                    DatasetFactory(organization=OrganizationFactory())]

        result = Dataset.objects.owned_by(org, user)

        self.assertEqual(len(result), 2)
        for dataset in result:
            self.assertIn(dataset, datasets)

        for dataset in excluded:
            self.assertNotIn(dataset, result)

    def test_add_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()

        dataset.add_resource(ResourceFactory())
        self.assertEqual(len(dataset.resources), 1)

        dataset.add_resource(resource)
        self.assertEqual(len(dataset.resources), 2)
        self.assertEqual(dataset.resources[0].id, resource.id)

    def test_last_update_with_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        dataset.add_resource(resource)
        self.assertEqualDates(dataset.last_update, resource.published)

    def test_last_update_without_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        self.assertEqualDates(dataset.last_update, dataset.last_modified)

    def test_add_community_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()

        dataset.add_community_resource(ResourceFactory())
        self.assertEqual(len(dataset.community_resources), 1)

        dataset.add_community_resource(resource)
        self.assertEqual(len(dataset.community_resources), 2)
        self.assertEqual(dataset.community_resources[0].id, resource.id)
