from flask import url_for

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import (DatasetFactory, LicenseFactory)
from udata.i18n import gettext as _

from . import APITestCase

class DataserviceAPITest(APITestCase):
    modules = []

    def test_dataset_api_create(self):
        self.login()
        datasets = DatasetFactory.create_batch(3)
        license = LicenseFactory.create()

        response = self.post(url_for('api.dataservices'), {
            'title': 'My API',
            'base_api_url': 'https://example.org',
        })
        self.assert201(response)
        self.assertEqual(Dataservice.objects.count(), 1)

        dataservice = Dataservice.objects.first()

        response = self.get(url_for('api.dataservice', dataservice=dataservice))
        self.assert200(response)

        self.assertEqual(response.json['title'], 'My API')
        self.assertEqual(response.json['base_api_url'], 'https://example.org')

        response = self.patch(url_for('api.dataservice', dataservice=dataservice), {
            'title': 'Updated title',
            'tags': ['hello', 'world'],
            'private': True,
            'datasets': [datasets[0].id, datasets[2].id],
            'license': license.id,
            'extras': {
                'foo': 'bar',
            }
        })
        self.assert200(response)

        self.assertEqual(response.json['title'], 'Updated title')
        self.assertEqual(response.json['base_api_url'], 'https://example.org')
        self.assertEqual(response.json['tags'], ['hello', 'world'])
        self.assertEqual(response.json['private'], True)
        self.assertEqual(response.json['datasets'][0]['title'], datasets[0].title)
        self.assertEqual(response.json['datasets'][1]['title'], datasets[2].title)
        self.assertEqual(response.json['extras'], {
            'foo': 'bar',
        })
        self.assertEqual(response.json['license'], license.title)
        dataservice.reload()
        self.assertEqual(dataservice.title, 'Updated title')
        self.assertEqual(dataservice.base_api_url, 'https://example.org')
        self.assertEqual(dataservice.tags, ['hello', 'world'])
        self.assertEqual(dataservice.private, True)
        self.assertEqual(dataservice.datasets[0].title, datasets[0].title)
        self.assertEqual(dataservice.datasets[1].title, datasets[2].title)
        self.assertEqual(dataservice.extras, {
            'foo': 'bar',
        })
        self.assertEqual(dataservice.license.title, license.title)

        response = self.delete(url_for('api.dataservice', dataservice=dataservice))
        self.assert204(response)

        self.assertEqual(Dataservice.objects.count(), 1)

        dataservice.reload()
        self.assertEqual(dataservice.title, 'Updated title')
        self.assertEqual(dataservice.base_api_url, 'https://example.org')
        self.assertIsNotNone(dataservice.deleted_at)

        # response = self.get(url_for('api.dataservice', dataservice=dataservice))
        # self.assert410(response)


    def test_dataset_api_create_with_validation_error(self):
        self.login()
        response = self.post(url_for('api.dataservices'), {
            'base_api_url': 'https://example.org',
        })
        self.assert400(response)
        self.assertEqual(Dataservice.objects.count(), 0)

    def test_dataset_api_create_with_unkwown_license(self):
        self.login()
        response = self.post(url_for('api.dataservices'), {
            'title': 'My title',
            'base_api_url': 'https://example.org',
            'license': 'unwkown-license',
        })
        self.assert400(response)
        self.assertEqual(response.json['errors']['license'], ["Unknown reference 'unwkown-license'"])
        self.assertEqual(Dataservice.objects.count(), 0)
