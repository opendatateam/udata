import json
from tempfile import NamedTemporaryFile

from udata import models
from udata.commands.fixtures import generate_fixtures
from udata.tests import TestCase, DBTestMixin


class FixturesTest(DBTestMixin, TestCase):

    def test_generate_fixtures(self):
        with NamedTemporaryFile(delete=True) as fixtures_fd:
            json_fixtures = [{
                "resources": [{
                        "description": "test description",
                        "filetype": "remote",
                        "title": "test",
                        "url": "https://dev.local"
                    }],
                "dataset": {
                    "description": "### Le Test",
                    "frequency": "punctual",
                    "tags": ["action-publique"],
                    "title": "test"
                    },
                "organization": {
                    "description": "test description",
                    "name": "Test"
                },
                "reuses": [{
                    "description": "test description",
                    "title": "test",
                    "url": "https://dev.local"
                    }]
                }]
            with open(fixtures_fd, 'w') as f:
                json.dump(json_fixtures, f)
            generate_fixtures(fixtures_fd)
            self.assertEqual(models.Organization.objects.count(), 1)
            self.assertEqual(models.Dataset.objects.count(), 1)
            self.assertEqual(models.Reuse.objects.count(), 1)
            self.assertEqual(models.User.objects.count(), 1)
