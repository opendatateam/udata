import requests
import logging
from ..harvesters.ods import OdsHarvester
from udata.tests import TestCase, DBTestMixin
from udata.models import db, Dataset, License

log = logging.getLogger(__name__)

class OdsHarvesterTest(DBTestMixin, TestCase):

	class Source(object):
		def __init__(self, url):
			self.url = url
			self.owner = None
			self.organization = None

	class Job(object):
		def __init__(self):
			self.items = []

		def save(self):
			pass

	def test_create_ods_url(self):
		self.assertEqual(OdsHarvester.create_ods_base_url("http://public.opendatasoft.com/api/datasets/1.0/search/?rows=10"), "http://public.opendatasoft.com")
		self.assertEqual(OdsHarvester.create_ods_base_url("https://public.opendatasoft.com/api/datasets/1.0/search/?rows=10"), "https://public.opendatasoft.com")
		self.assertEqual(OdsHarvester.create_ods_base_url("http://public.opendatasoft.com/explore/"), "http://public.opendatasoft.com")
		self.assertEqual(OdsHarvester.create_ods_base_url("http://public.opendatasoft.com"), "http://public.opendatasoft.com")
	
	def test_simple(self):
		# Create fake licenses
		for license_id in OdsHarvester.LICENSES.values():
			License.objects.create(id=license_id, title=license_id)
		self.assertEqual(len(Dataset.objects.all()), 0)
		source = OdsHarvesterTest.Source("http://etalab-sandbox.opendatasoft.com")
		job = OdsHarvesterTest.Job()
		harvester = OdsHarvester(source, job)
		harvester.initialize()

		self.assertEqual(len(harvester.job.items), 3)
		harvester.process_items()
		datasets = {d.extras["remote_id"]:d for d in Dataset.objects.all()}
		self.assertEqual(len(datasets), 3)

		self.assertTrue("test-a@etalab-sandbox" in datasets)
		test_a = datasets["test-a@etalab-sandbox"]
		self.assertEqual(test_a.title, "test-a")
		self.assertEqual(test_a.description, "<p>test-a-description</p>")
		self.assertEqual(",".join(test_a.tags), "environment,keyword2,keyword1,heritage,culture")
		self.assertEqual(test_a.extras["references"], "http://example.com")
		self.assertEqual(test_a.extras["has_records"], True)
		self.assertEqual(test_a.extras["remote_id"], "test-a@etalab-sandbox")
		self.assertEqual(test_a.extras["ods_url"], "http://etalab-sandbox.opendatasoft.com/explore/dataset/test-a/")
		self.assertEqual(test_a.license.id, "fr-lo")

		self.assertEqual(len(test_a.resources), 1)
		resource = test_a.resources[0]
		self.assertEqual(resource.title, test_a.title)
		self.assertEqual(resource.description, test_a.description)
		self.assertEqual(resource.url, "http://etalab-sandbox.opendatasoft.com/explore/dataset/test-a/?tab=export")
		resp = requests.get(resource.url)
		resp.raise_for_status()


		self.assertTrue("test-b@etalab-sandbox" in datasets)
		test_b = datasets["test-b@etalab-sandbox"]
		self.assertEqual(",".join(test_b.tags), "buildings,housing,equipment,town planning,keyword1,spatial planning")
		self.assertEqual(len(test_b.resources), 1)
		resource = test_b.resources[0]
		self.assertEqual(resource.title, test_b.title)
		self.assertEqual(resource.url, "http://etalab-sandbox.opendatasoft.com/explore/dataset/test-b/?tab=export")
		resp = requests.get(resource.url)
		resp.raise_for_status()

		test_c = datasets["test-c@etalab-sandbox"]
		self.assertEqual(len(test_c.resources), 1)
		resource = test_c.resources[0]
		self.assertEqual(resource.format, "html")
		self.assertEqual(resource.url, "http://etalab-sandbox.opendatasoft.com/explore/dataset/test-c/?tab=export")



