# -*- coding: utf-8 -*-

from .. import TestCase, SearchTestMixin

from udata.models import Dataset, Organization
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.organization import tasks
from udata.search import es


class OrganizationTasksTest(SearchTestMixin, TestCase):
    def test_purge_organizations(self):
        with self.autoindex():
            org = Organization.objects.create(
                name='delete me', deleted='2016-01-01', description='XXX')
            resources = [ResourceFactory() for _ in range(2)]
            dataset = DatasetFactory(resources=resources, organization=org)

        tasks.purge_organizations()

        dataset = Dataset.objects(id=dataset.id).first()
        self.assertIsNone(dataset.organization)

        organization = Organization.objects(name='delete me').first()
        self.assertIsNone(organization)

        indexed_dataset = DatasetSearch.get(id=dataset.id,
                                            using=es.client,
                                            index=es.index_name)
        self.assertIsNone(indexed_dataset.organization)
