from flask import url_for

from udata.tests.api import APITestCase

from udata.core import storages
from udata.tests.helpers import create_test_image
from udata.models import Dataset, Organization
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.user.factories import AdminFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.organization import tasks
from udata.search import es


class OrganizationTasksTest(APITestCase):
    def test_purge_organizations(self):
        with self.autoindex():
            org = Organization.objects.create(name='delete me', description='XXX')
            resources = [ResourceFactory() for _ in range(2)]
            dataset = DatasetFactory(resources=resources, organization=org)

        # Upload organization's logo
        file = create_test_image()
        user = AdminFactory()
        self.login(user)
        response = self.post(
            url_for('api.organization_logo', org=org),
            {'file': (file, 'test.png')},
            json=False)
        self.assert200(response)

        # Delete organization
        response = self.delete(url_for('api.organization', org=org))
        self.assert204(response)

        tasks.purge_organizations()

        # Check organization's logo is deleted
        self.assertEqual(list(storages.avatars.list_files()), [])

        dataset = Dataset.objects(id=dataset.id).first()
        self.assertIsNone(dataset.organization)

        organization = Organization.objects(name='delete me').first()
        self.assertIsNone(organization)

        indexed_dataset = DatasetSearch.get(id=dataset.id,
                                            using=es.client,
                                            index=es.index_name)
        self.assertIsNone(indexed_dataset.organization)
