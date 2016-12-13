from __future__ import unicode_literals

import logging

from datetime import datetime
from os.path import join, dirname

import httpretty

from udata.models import Dataset, License
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory

from .factories import HarvestSourceFactory
from .. import actions
from ..backends.ods import OdsHarvester

log = logging.getLogger(__name__)


ODS_URL = 'http://etalab-sandbox.opendatasoft.com'

json_filename = join(dirname(__file__), 'search-ods.json')
with open(json_filename) as f:
    ODS_RESPONSE = f.read()


class OdsHarvesterTest(DBTestMixin, TestCase):
    def setUp(self):
        # Create fake licenses
        for license_id in OdsHarvester.LICENSES.values():
            License.objects.create(id=license_id, title=license_id)

    @httpretty.activate
    def test_simple(self):
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='ods',
                                      url=ODS_URL,
                                      organization=org)

        api_url = ''.join((ODS_URL, '/api/datasets/1.0/search/'))
        httpretty.register_uri(httpretty.GET, api_url,
                               body=ODS_RESPONSE,
                               content_type='application/json')

        actions.run(source.slug)

        self.assertEqual(
            httpretty.last_request().querystring,
            {'start': ['0'], 'rows': ['50']}
        )

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 3)
        self.assertEqual(job.status, 'done')

        datasets = {d.extras["harvest:remote_id"]: d for d in Dataset.objects}
        self.assertEqual(len(datasets), 2)

        self.assertIn("test-a", datasets)
        d = datasets["test-a"]
        self.assertEqual(d.title, "test-a")
        self.assertEqual(d.description, "test-a-description")
        self.assertEqual(d.tags, ['culture',
                                  'environment',
                                  'heritage',
                                  'keyword1',
                                  'keyword2'])
        self.assertEqual(d.extras["ods:references"], "http://example.com")
        self.assertTrue(d.extras["ods:has_records"])
        self.assertEqual(d.extras["harvest:remote_id"], "test-a")
        self.assertEqual(d.extras["harvest:domain"],
                         "etalab-sandbox.opendatasoft.com")
        self.assertEqual(d.extras["ods:url"],
                         ("http://etalab-sandbox.opendatasoft.com"
                          "/explore/dataset/test-a/"))
        self.assertEqual(d.license.id, "fr-lo")

        self.assertEqual(len(d.resources), 2)
        resource = d.resources[0]
        self.assertEqual(resource.title, 'Export au format CSV')
        self.assertIsNotNone(resource.description)
        self.assertEqual(resource.format, 'csv')
        self.assertEqual(resource.mime, 'text/csv')
        self.assertIsInstance(resource.modified, datetime)
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-a/download"
                          "?format=csv&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))

        resource = d.resources[1]
        self.assertEqual(resource.title, 'Export au format JSON')
        self.assertIsNotNone(resource.description)
        self.assertEqual(resource.format, 'json')
        self.assertEqual(resource.mime, 'application/json')
        self.assertIsInstance(resource.modified, datetime)
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-a/download"
                          "?format=json&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))

        # test-b has geo feature
        self.assertIn("test-b", datasets)
        test_b = datasets["test-b"]
        self.assertEqual(test_b.tags, ['buildings',
                                       'equipment',
                                       'housing',
                                       'keyword1',
                                       'spatial-planning',
                                       'town-planning'])
        self.assertEqual(len(test_b.resources), 4)
        resource = test_b.resources[2]
        self.assertEqual(resource.title, 'Export au format GeoJSON')
        self.assertIsNotNone(resource.description)
        self.assertEqual(resource.format, 'json')
        self.assertEqual(resource.mime, 'application/vnd.geo+json')
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-b/download"
                          "?format=geojson&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))
        resource = test_b.resources[3]
        self.assertEqual(resource.title, 'Export au format Shapefile')
        self.assertIsNotNone(resource.description)
        self.assertEqual(resource.format, 'shp')
        self.assertIsNone(resource.mime)
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-b/download"
                          "?format=shp&timezone=Europe/Berlin"
                          "&use_labels_for_header=true"))

        # test-c has no data
        self.assertNotIn('test-c', datasets)
