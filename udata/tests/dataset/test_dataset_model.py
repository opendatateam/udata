# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from mongoengine import post_save

from udata.models import Dataset, CommunityResource

from .. import TestCase, DBTestMixin
from ..factories import (
    ResourceFactory, DatasetFactory, UserFactory, OrganizationFactory,
    CommunityResourceFactory
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
        expected_signals = post_save, Dataset.after_save, Dataset.on_update

        with self.assert_emit(*expected_signals):
            dataset.add_resource(ResourceFactory())
        self.assertEqual(len(dataset.resources), 1)

        with self.assert_emit(*expected_signals):
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

    def test_community_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        community_resource1 = CommunityResourceFactory()
        community_resource1.dataset = dataset
        community_resource1.save()
        self.assertEqual(len(dataset.community_resources), 1)

        community_resource2 = CommunityResourceFactory()
        community_resource2.dataset = dataset
        community_resource2.save()
        self.assertEqual(len(dataset.community_resources), 2)
        self.assertEqual(dataset.community_resources[0].id,
                         community_resource1.id)
        self.assertEqual(dataset.community_resources[1].id,
                         community_resource2.id)
