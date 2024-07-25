import json
from tempfile import NamedTemporaryFile

import pytest

from udata import models
from udata.tests import DBTestMixin, TestCase


class FixturesTest(DBTestMixin):
    @pytest.mark.datagouvfr
    @pytest.mark.options(FIXTURE_DATASET_SLUGS=["nombre-de-personnes-rickrollees-sur-data-gouv-fr"])
    def test_generate_fixtures_file_and_generate_fixtures(self, cli):
        with NamedTemporaryFile(mode="w+", delete=True) as fixtures_fd:
            # Get the fixtures from http://data.gouv.fr.
            result = cli("generate-fixtures-file", "http://data.gouv.fr", fixtures_fd.name)
            fixtures_fd.flush()
            assert "Fixtures saved to file " in result.output

            # Then load them in the database to make sure they're correct.
            result = cli("generate-fixtures", fixtures_fd.name)
            assert models.Organization.objects(slug="data-gouv-fr").count() > 0
            assert models.Dataset.objects.count() > 0
            assert models.Discussion.objects.count() > 0
            assert models.CommunityResource.objects.count() > 0
            assert models.User.objects.count() > 0
