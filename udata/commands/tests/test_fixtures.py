from tempfile import NamedTemporaryFile

import pytest
import requests
from werkzeug.wrappers.response import Response

from udata import models
from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DatasetBloc,
    ExploreBloc,
    HeroBloc,
    LinkInBloc,
    LinksListBloc,
    SectionBloc,
    TitleBloc,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.post.factories import PostFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.factories import SiteFactory
from udata.core.spam.models import SpamMixin
from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyAPITestCase


class FixturesTest(PytestOnlyAPITestCase):
    @pytest.mark.options(FIXTURE_DATASET_SLUGS=["some-test-dataset-slug"])
    def test_generate_fixtures_file_then_import(self, mocker):
        """Test generating fixtures from the current env, then importing them back."""
        assert models.Dataset.objects.count() == 0  # Start with a clean slate.
        user = UserFactory()
        admin = UserFactory()
        org = OrganizationFactory(
            members=[Member(user=user, role="editor"), Member(user=admin, role="admin")]
        )
        contact_point = ContactPointFactory(role="contact", organization=org)
        # Set the same slug we're 'exporting' from the FIXTURE_DATASET_SLUG config, see the
        # @pytest.mark.options above.
        dataset = DatasetFactory(
            slug="some-test-dataset-slug", organization=org, contact_points=[contact_point]
        )
        res = ResourceFactory()
        dataset.add_resource(res)
        # Not exported: neither is the resource an explorer shows
        not_exported = DatasetFactory(resources=[ResourceFactory()])
        ReuseFactory(datasets=[dataset], owner=user)
        CommunityResourceFactory(dataset=dataset, owner=user)
        DiscussionFactory(
            **{},
            subject=dataset,
            user=user,
            discussion=[
                MessageDiscussionFactory(posted_by=user),
                MessageDiscussionFactory(posted_by=admin),
            ],
            closed_by=admin,
        )
        DataserviceFactory(datasets=[dataset], organization=org, contact_points=[contact_point])

        PostFactory(
            name="Test Post",
            headline="A test post",
            owner=user,
            content="Some content",
        )
        sub_page = PostFactory(kind="page", parent=PostFactory(kind="page"))
        SiteFactory(
            id=self.app.config["SITE_ID"],
            title="Test Site",
            datasets_blocs=[
                HeroBloc(title="Test Hero", description="A test hero bloc"),
                SectionBloc(
                    blocs=[
                        TitleBloc(title="Test Links"),
                        LinksListBloc(
                            links=[LinkInBloc(title="Example", url="https://example.com")],
                        ),
                        # The fixtures don't hold the dataset: the bloc showing it goes.
                        DatasetBloc(dataset=dataset),
                        ExploreBloc(resource_id=res.id),
                        # Nor the resource: the explorer goes, it would not import.
                        ExploreBloc(resource_id=not_exported.resources[0].id),
                    ]
                ),
                SectionBloc(
                    blocs=[
                        TitleBloc(title="Accordion"),
                        # So does the item holding it, then the accordion left empty.
                        AccordionListBloc(
                            items=[
                                AccordionItemBloc(
                                    title="Item", content=[DatasetBloc(dataset=dataset)]
                                )
                            ]
                        ),
                    ]
                ),
            ],
        )

        with NamedTemporaryFile(mode="w+", delete=True) as fixtures_fd:
            # Get the fixtures from the local instance by redirecting requests.get to the test client
            mocker.patch.object(requests, "get", side_effect=lambda url, **kw: self.get(url, **kw))
            mocker.patch.object(Response, "json", Response.get_json)
            mocker.patch.object(Response, "ok", True, create=True)
            result = self.cli("generate-fixtures-file", "", fixtures_fd.name)
            fixtures_fd.flush()
            assert "Fixtures saved to file " in result.output

            # Delete everything, so we can make sure the objects are imported.
            models.Organization.drop_collection()
            models.Dataset.drop_collection()
            models.Discussion.drop_collection()
            models.CommunityResource.drop_collection()
            models.User.drop_collection()
            models.Dataservice.drop_collection()
            models.ContactPoint.drop_collection()
            models.Post.drop_collection()
            models.Site.drop_collection()

            assert models.Organization.objects(slug=org.slug).count() == 0
            assert models.Dataset.objects.count() == 0
            assert models.Discussion.objects.count() == 0
            assert models.CommunityResource.objects.count() == 0
            assert models.User.objects.count() == 0
            assert models.Dataservice.objects.count() == 0
            assert models.ContactPoint.objects.count() == 0
            assert models.Post.objects.count() == 0
            assert models.Site.objects.count() == 0

            # Then load them in the database to make sure they're correct.
            result = self.cli("import-fixtures", fixtures_fd.name)
        assert models.Organization.objects(slug=org.slug).count() > 0
        result_org = models.Organization.objects.get(slug=org.slug)
        assert result_org.members[0].user.id == user.id
        assert result_org.members[0].role == "editor"
        assert result_org.members[1].user.id == admin.id
        assert result_org.members[1].role == "admin"
        assert models.Dataset.objects.count() > 0
        result_dataset = models.Dataset.objects.first()
        assert result_dataset.contact_points == [contact_point]
        assert models.Discussion.objects.count() > 0
        result_discussion = models.Discussion.objects.first()
        assert result_discussion.user.id == user.id
        assert result_discussion.closed_by.id == admin.id
        assert len(result_discussion.discussion) == 2
        assert result_discussion.discussion[0].posted_by.id == user.id
        assert result_discussion.discussion[1].posted_by.id == admin.id
        assert models.CommunityResource.objects.count() > 0
        assert models.User.objects.count() > 0
        assert models.Dataservice.objects.count() > 0
        # Make sure we also import the dataservice organization
        result_dataservice = models.Dataservice.objects.first()
        assert result_dataservice.organization == org
        assert result_dataservice.contact_points == [contact_point]

        assert models.Post.objects(name="Test Post").count() == 1
        # The parent is not exported, so the pages tree is flattened on import
        assert models.Post.objects.get(id=sub_page.id).parent is None

        assert models.Site.objects.count() > 0
        result_site = models.Site.objects.first()
        hero, section, accordion_section = result_site.datasets_blocs
        assert hero.title == "Test Hero"
        title, links, explore = section.blocs
        assert title.title == "Test Links"
        assert links.links[0].url == "https://example.com"
        assert explore.resource_id == res.id
        assert [bloc.title for bloc in accordion_section.blocs] == ["Accordion"]

    def test_import_fixtures_from_default_file(self):
        """Test importing fixtures from udata.commands.fixture.DEFAULT_FIXTURE_FILE."""
        # Deactivate spam detection when testing import fixtures
        SpamMixin.detect_spam_enabled = False
        self.cli("import-fixtures")
        SpamMixin.detect_spam_enabled = True
        assert models.Organization.objects.count() > 0
        assert models.Dataset.objects.count() > 0
        assert models.Reuse.objects.count() > 0
        assert models.User.objects.count() > 0
        assert models.Dataservice.objects.count() > 0
        assert models.Post.objects.count() > 0
        assert models.Site.objects.count() > 0
        # The edito pages of the site, their lists stripped at export
        first, *_ = models.Site.objects.get().datasets_blocs
        title, *rest = first.blocs
        assert (title.title, title.subtitle) == (
            "Jeux de données populaires",
            "Découvrez quelques-uns des jeux de données les plus populaires sur la plateforme.",
        )
        assert rest == []
