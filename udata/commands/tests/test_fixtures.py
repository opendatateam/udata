from tempfile import NamedTemporaryFile

import pytest
import requests
from werkzeug.wrappers.response import Response

import udata.commands.fixtures
from udata import models
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory


@pytest.mark.usefixtures("clean_db")
class FixturesTest:
    @pytest.mark.frontend
    @pytest.mark.options(FIXTURE_DATASET_SLUGS=["some-test-dataset-slug"])
    def test_generate_fixtures_file_then_import(self, app, cli, api, monkeypatch):
        """Test generating fixtures from the current env, then importing them back."""
        assert models.Dataset.objects.count() == 0  # Start with a clean slate.
        user = UserFactory()
        org = OrganizationFactory(**{}, members=[Member(user=user)])
        # Set the same slug we're 'exporting' from the FIXTURE_DATASET_SLUG config, see the
        # @pytest.mark.options above.
        dataset = DatasetFactory(**{}, slug="some-test-dataset-slug", organization=org)
        res = ResourceFactory(**{})
        dataset.add_resource(res)
        ReuseFactory(**{}, datasets=[dataset], owner=user)
        CommunityResourceFactory(**{}, dataset=dataset, owner=user)
        DiscussionFactory(
            **{},
            subject=dataset,
            user=user,
            discussion=[MessageDiscussionFactory(**{}, posted_by=user)],
        )
        DataserviceFactory(**{}, datasets=[dataset])

        with NamedTemporaryFile(mode="w+", delete=True) as fixtures_fd:
            # Get the fixtures from the local instance.
            monkeypatch.setattr(requests, "get", lambda url: api.get(url))
            monkeypatch.setattr(Response, "json", Response.get_json)
            result = cli("generate-fixtures-file", "", fixtures_fd.name)
            fixtures_fd.flush()
            assert "Fixtures saved to file " in result.output

            # Then load them in the database to make sure they're correct.
            result = cli("import-fixtures", fixtures_fd.name)
        assert models.Organization.objects(slug=org.slug).count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Discussion.objects.count() > 0
        assert models.CommunityResource.objects.count() > 0
        assert models.User.objects.count() > 0
        assert models.Dataservice.objects.count() > 0

    def test_import_fixtures_from_default_file(self, cli):
        """Test importing fixtures from udata.commands.fixture.DEFAULT_FIXTURE_FILE."""
        cli("import-fixtures")
        assert models.Organization.objects.count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Reuse.objects.count() > 0
        assert models.User.objects.count() > 0
        if udata.commands.fixtures.DEFAULT_FIXTURE_FILE_TAG > "v1.0.0":
            assert models.Dataservice.objects.count() > 0
