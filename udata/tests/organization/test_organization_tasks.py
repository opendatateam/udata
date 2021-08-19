from flask import url_for

from udata.api.oauth2 import OAuth2Client
from udata.core import storages
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.user.factories import AdminFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.organization import tasks
from udata.models import Dataset, Organization, Transfer
from udata.tests.api import APITestCase
from udata.search import es
from udata.tests.helpers import create_test_image


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

        transfer_to_org = Transfer.objects.create(
            owner=user,
            recipient=org,
            subject=dataset,
            comment='comment',
        )
        transfer_from_org = Transfer.objects.create(
            owner=org,
            recipient=user,
            subject=dataset,
            comment='comment',
        )

        oauth_client = OAuth2Client.objects.create(
            name='test-client',
            owner=user,
            organization=org,
            redirect_uris=['https://test.org/callback'],
        )

        # Delete organization
        response = self.delete(url_for('api.organization', org=org))
        self.assert204(response)

        tasks.purge_organizations()

        oauth_client.reload()
        assert oauth_client.organization is None

        assert Transfer.objects.filter(id=transfer_from_org.id).count() == 0
        assert Transfer.objects.filter(id=transfer_to_org.id).count() == 0

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
