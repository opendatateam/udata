from udata.settings import Defaults
from udata.tasks import default_scheduler_config
from udata.tests import TestCase


class DefaultSchedulerConfigTest(TestCase):
    def test_parse_default_value(self):
        db, url = default_scheduler_config(Defaults.MONGODB_HOST)
        self.assertEqual(db, "udata")
        self.assertEqual(url, "mongodb://localhost:27017")

    def test_parse_url_with_auth(self):
        full_url = "mongodb://userid:password@somewhere.com:1234/mydb"
        db, url = default_scheduler_config(full_url)
        self.assertEqual(db, "mydb")
        self.assertEqual(url, "mongodb://userid:password@somewhere.com:1234")
