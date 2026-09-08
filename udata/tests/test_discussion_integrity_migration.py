from mongoengine.connection import get_db

from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.models import Discussion
from udata.core.organization.factories import OrganizationFactory
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-09-02-discussion-integrity.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def reloaded(discussion):
    """Reload the discussion, dereferencing organizations as the API does.

    A dangling reference raises `DoesNotExist` on access, which is the 500 this migration
    exists to make impossible.
    """
    return Discussion.objects.get(id=discussion.id)


class DiscussionOrganizationTest(PytestOnlyDBTestCase):
    def test_discussion_opened_on_behalf_of_a_deleted_organization_is_removed(self):
        org = OrganizationFactory()
        discussion = DiscussionFactory(organization=org)
        org.delete()

        migrate()

        assert Discussion.objects(id=discussion.id).first() is None

    def test_discussion_of_a_live_organization_is_left_alone(self):
        org = OrganizationFactory()
        discussion = DiscussionFactory(organization=org)

        migrate()

        assert reloaded(discussion).organization == org


class MessagePostedByOrganizationTest(PytestOnlyDBTestCase):
    def test_message_posted_on_behalf_of_a_deleted_organization_is_unset(self):
        org = OrganizationFactory()
        discussion = DiscussionFactory(
            discussion=[MessageDiscussionFactory(posted_by_organization=org)]
        )
        org.delete()

        migrate()

        assert reloaded(discussion).discussion[0].posted_by_organization is None

    def test_thread_mixing_plain_and_on_behalf_messages_is_cleaned_too(self):
        """The common shape: someone opens a thread, an organization member answers."""
        org = OrganizationFactory()
        discussion = DiscussionFactory(
            discussion=[
                MessageDiscussionFactory(),
                MessageDiscussionFactory(posted_by_organization=org),
            ]
        )
        org.delete()

        migrate()

        messages = reloaded(discussion).discussion
        assert messages[0].posted_by_organization is None
        assert messages[1].posted_by_organization is None

    def test_message_of_a_live_organization_is_left_alone(self):
        org = OrganizationFactory()
        discussion = DiscussionFactory(
            discussion=[
                MessageDiscussionFactory(),
                MessageDiscussionFactory(posted_by_organization=org),
            ]
        )

        migrate()

        assert reloaded(discussion).discussion[1].posted_by_organization == org


class ClosedByOrganizationTest(PytestOnlyDBTestCase):
    def test_closed_on_behalf_of_a_deleted_organization_is_unset(self):
        org = OrganizationFactory()
        discussion = DiscussionFactory(closed_by_organization=org)
        org.delete()

        migrate()

        assert reloaded(discussion).closed_by_organization is None

    def test_closed_by_a_live_organization_is_left_alone(self):
        org = OrganizationFactory()
        discussion = DiscussionFactory(closed_by_organization=org)

        migrate()

        assert reloaded(discussion).closed_by_organization == org
