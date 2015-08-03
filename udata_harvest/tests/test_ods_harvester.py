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

    def test_create_ods_url(self):
        values = {
            "http://public.opendatasoft.com/api/datasets/1.0/search/?rows=10":
                "http://public.opendatasoft.com",
            "https://public.opendatasoft.com/api/datasets/1.0/search/?rows=10":
                "https://public.opendatasoft.com",
            "http://public.opendatasoft.com/explore/":
                "http://public.opendatasoft.com",
            "http://public.opendatasoft.com": "http://public.opendatasoft.com",
        }
        for value, expected in values.items():
            self.assertEqual(OdsHarvester.create_ods_base_url(value), expected)

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

        datasets = {d.extras["remote_id"]: d for d in Dataset.objects.all()}
        self.assertEqual(len(datasets), 3)

        self.assertTrue("test-a@etalab-sandbox" in datasets)
        d = datasets["test-a@etalab-sandbox"]
        self.assertEqual(d.title, "test-a")
        self.assertEqual(d.description, "<p>test-a-description</p>")
        self.assertEqual(",".join(d.tags),
                         "environment,keyword2,keyword1,heritage,culture")
        self.assertEqual(d.extras["references"], "http://example.com")
        self.assertEqual(d.extras["has_records"], True)
        self.assertEqual(d.extras["remote_id"], "test-a@etalab-sandbox")
        self.assertEqual(d.extras["ods_url"],
                         ("http://etalab-sandbox.opendatasoft.com"
                          "/explore/dataset/test-a/"))
        self.assertEqual(d.license.id, "fr-lo")

        self.assertEqual(len(d.resources), 1)
        resource = d.resources[0]
        self.assertEqual(resource.title, d.title)
        self.assertEqual(resource.description, d.description)
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-a/?tab=export"))
        resp = requests.get(resource.url)
        resp.raise_for_status()

        self.assertTrue("test-b@etalab-sandbox" in datasets)
        test_b = datasets["test-b@etalab-sandbox"]
        self.assertEqual(",".join(test_b.tags),
                         ("buildings,housing,equipment,town planning,"
                          "keyword1,spatial planning"))
        self.assertEqual(len(test_b.resources), 1)
        resource = test_b.resources[0]
        self.assertEqual(resource.title, test_b.title)
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com/"
                          "explore/dataset/test-b/?tab=export"))
        resp = requests.get(resource.url)
        resp.raise_for_status()

        test_c = datasets["test-c@etalab-sandbox"]
        self.assertEqual(len(test_c.resources), 1)
        resource = test_c.resources[0]
        self.assertEqual(resource.format, "html")
        self.assertEqual(resource.url,
                         ("http://etalab-sandbox.opendatasoft.com"
                          "/explore/dataset/test-c/?tab=export"))
