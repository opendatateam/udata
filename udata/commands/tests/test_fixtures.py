import json
from tempfile import NamedTemporaryFile

from udata import models
from udata.tests import DBTestMixin, TestCase


class FixturesTest(DBTestMixin):
    def test_import_fixtures(self, cli):
        cli("import-fixtures")
        assert models.Organization.objects.count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Reuse.objects.count() > 0
        assert models.User.objects.count() > 0
