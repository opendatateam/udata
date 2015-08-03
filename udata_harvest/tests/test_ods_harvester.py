from __future__ import unicode_literals

import requests
import json
import logging

from os.path import join, dirname

from mock import patch

from udata.models import Dataset, License
from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import OrganizationFactory

from .factories import HarvestSourceFactory
from .. import actions
from ..backends.ods import OdsHarvester

log = logging.getLogger(__name__)


ODS_URL = 'http://etalab-sandbox.opendatasoft.com'

json_filename = join(dirname(__file__), 'search-ods.json')
with open(json_filename) as f:
    ODS_RESPONSE = json.load(f)


class OdsHarvesterTest(DBTestMixin, TestCase):
    def setUp(self):
        # Create fake licenses
        for license_id in OdsHarvester.LICENSES.values():
            License.objects.create(id=license_id, title=license_id)

    @patch.object(OdsHarvester, 'get')
    def test_simple(self, mock):
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='ods',
                                      url=ODS_URL,
                                      organization=org)
        mock.return_value.json.return_value = ODS_RESPONSE

        actions.run(source.slug)

        api_url = ''.join((ODS_URL, '/api/datasets/1.0/search/'))
        params = {'start': 0, 'rows': 50}
        mock.assert_called_once_with(api_url, params=params)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 3)

        datasets = {d.extras["harvest:remote_id"]: d for d in Dataset.objects}
        self.assertEqual(len(datasets), 2)

        self.assertIn("test-a", datasets)
        d = datasets["test-a"]
        self.assertEqual(d.title, "test-a")
        self.assertEqual(d.description, "<p>test-a-description</p>")
        self.assertEqual(d.tags, ['environment',
                                  'keyword2',
                                  'keyword1',
                                  'heritage',
                                  'culture'])
        self.assertEqual(d.extras["references"], "http://example.com")
        self.assertEqual(d.extras["has_records"], True)
        self.assertEqual(d.extras["harvest:remote_id"], "test-a")
        self.assertEqual(d.extras["harvest:domain"],
                         "etalab-sandbox.opendatasoft.com")
        self.assertEqual(d.extras["ods_url"],
                         ("http://etalab-sandbox.opendatasoft.com"
                          "/explore/dataset/test-a/"))
        self.assertEqual(d.license.id, "fr-lo")

        self.assertEqual(len(d.resources), 2)
        resource = d.resources[0]
        self.assertEqual(resource.title, '{0} (CSV)'.format(d.title))
        self.assertEqual(resource.description, d.description)
        self.assertEqual(resource.format, 'csv')
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-a/download"
                          "?format=csv&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))

        resource = d.resources[1]
        self.assertEqual(resource.title, '{0} (JSON)'.format(d.title))
        self.assertEqual(resource.description, d.description)
        self.assertEqual(resource.format, 'json')
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-a/download"
                          "?format=json&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))

        # test-b has geo feature
        self.assertIn("test-b", datasets)
        test_b = datasets["test-b"]
        self.assertEqual(test_b.tags, ['buildings',
                                       'housing',
                                       'equipment',
                                       'town planning',
                                       'keyword1',
                                       'spatial planning'])
        self.assertEqual(len(test_b.resources), 3)
        resource = test_b.resources[2]
        self.assertEqual(resource.title, '{0} (GeoJSON)'.format(test_b.title))
        self.assertEqual(resource.description, test_b.description)
        self.assertEqual(resource.format, 'json')
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-b/download"
                          "?format=geojson&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))

        # test-c has no data
        self.assertNotIn('test-c', datasets)
