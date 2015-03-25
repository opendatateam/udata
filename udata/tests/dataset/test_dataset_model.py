# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Dataset

from .. import TestCase, DBTestMixin
from ..factories import ResourceFactory, DatasetFactory, UserFactory, OrganizationFactory


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
        datasets = [DatasetFactory(owner=user), DatasetFactory(organization=org)]
        excluded = [DatasetFactory(owner=UserFactory()), DatasetFactory(organization=OrganizationFactory())]

        result = Dataset.objects.owned_by(org, user)

        self.assertEqual(len(result), 2)
        for dataset in result:
            self.assertIn(dataset, datasets)

        for dataset in excluded:
            self.assertNotIn(dataset, result)
