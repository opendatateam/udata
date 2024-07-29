import json
from tempfile import NamedTemporaryFile

import pytest
import requests
import werkzeug.test
from pytest_mock import MockerFixture
from werkzeug.wrappers.response import Response

from udata import models
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member, Organization
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.tests import DBTestMixin, TestCase
from udata.tests.api import APITestCase
from udata.tests.plugin import ApiClient


@pytest.mark.usefixtures("clean_db")
class FixturesTest(APITestCase):
    @pytest.fixture(autouse=True)
    def init_fixtures(self, app, cli, mocker: MockerFixture, monkeypatch):
        self.app = app
        self.cli = cli
        self.mocker = mocker
        self.monkeypatch = monkeypatch

    def test_generate_fixtures_file_then_import(self) -> None:
        """Test generating fixtures from the current env, then importing them back."""
        assert models.Dataset.objects.count() == 0  # Start with a clean slate.
        user = UserFactory()
        org = OrganizationFactory(**{}, members=[Member(user=user)])
        dataset = DatasetFactory(**{}, organization=org)
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

        self.monkeypatch.setitem(self.app.config, "FIXTURE_DATASET_SLUGS", [dataset.slug])

        with NamedTemporaryFile(mode="w+", delete=True) as fixtures_fd:
            # Get the fixtures from the local instance.
            get_fixtures_mock = self.mocker.patch.object(requests, "get", lambda url: self.get(url))
            json_mock = self.mocker.patch.object(Response, "json", Response.get_json)
            result = self.cli("generate-fixtures-file", "", fixtures_fd.name)
            fixtures_fd.flush()
            assert "Fixtures saved to file " in result.output

            # Then load them in the database to make sure they're correct.
            result = self.cli("import-fixtures", fixtures_fd.name)
        assert models.Organization.objects(slug=org.slug).count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Discussion.objects.count() > 0
        assert models.CommunityResource.objects.count() > 0
        assert models.User.objects.count() > 0

    def test_import_fixtures_from_default_file(self):
        """Test importing fixtures from udata.commands.fixture.DEFAULT_FIXTURE_FILE."""
        self.cli("import-fixtures")
        assert models.Organization.objects.count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Reuse.objects.count() > 0
        assert models.User.objects.count() > 0
