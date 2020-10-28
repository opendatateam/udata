from flask import url_for

from udata.tests.api import APITestCase

from udata.core import storages
from udata.tests.helpers import create_test_image
from udata.models import Dataset, Reuse
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import AdminFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.dataset.search import DatasetSearch
from udata.core.reuse import tasks
from udata.search import es


class ReuseTasksTest(APITestCase):
    def test_purge_reuses(self):
        reuse = ReuseFactory(title='test-reuse')

        # Upload reuse's image
        file = create_test_image()
        user = AdminFactory()
        self.login(user)
        response = self.post(
            url_for('api.reuse_image', reuse=reuse),
            {'file': (file, 'test.png')},
            json=False)
        self.assert200(response)

        # Delete reuse
        response = self.delete(url_for('api.reuse', reuse=reuse))
        self.assert204(response)

        tasks.purge_reuses()

        # Check reuse's image is deleted
        self.assertEqual(list(storages.images.list_files()), [])

        deleted_reuse = Reuse.objects(title='test-reuse').first()
        self.assertIsNone(deleted_reuse)
