import json
from tempfile import NamedTemporaryFile

from udata import models
from udata.tests import DBTestMixin, TestCase


class FixturesTest(DBTestMixin):
    def test_generate_fixtures(self, cli):
        cli("generate-fixtures")
        assert models.Organization.objects.count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Reuse.objects.count() > 0
        assert models.User.objects.count() > 0
