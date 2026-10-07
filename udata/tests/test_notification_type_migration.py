from mongoengine.connection import get_db

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.db.migrations import load_migration
from udata.features.notifications.constants import NotificationType
from udata.tests.api import PytestOnlyDBTestCase


class SetNotificationTypeMigrationTest(PytestOnlyDBTestCase):
    """`type` is required now, so the model cannot produce a pre-migration document:
    the fixtures below are written straight to the collection."""

    def insert(self, details):
        return (
            get_db()
            .notification.insert_one({"user": UserFactory().id, "details": details})
            .inserted_id
        )

    def run_migration(self):
        load_migration("2026-09-15-set-notification-type.py").migrate(get_db())

    def stored(self, notification_id):
        return get_db().notification.find_one({"_id": notification_id})

    def test_the_type_is_derived_from_the_discriminator_which_stays_in_place(self):
        closed = self.insert(
            {"_cls": "DiscussionNotificationDetails", "status": "closed", "discussion": None}
        )
        certified = self.insert(
            {
                "_cls": "NewBadgeNotificationDetails",
                "kind": "certified",
                "organization": OrganizationFactory().id,
            }
        )

        self.run_migration()

        assert self.stored(closed)["type"] == NotificationType.DISCUSSION_CLOSED
        assert self.stored(closed)["details"]["status"] == "closed"
        assert self.stored(certified)["type"] == NotificationType.ORGANIZATION_BADGE_CERTIFIED
        assert self.stored(certified)["details"]["kind"] == "certified"

    def test_a_missing_discriminator_falls_back_on_the_value_it_defaulted_to(self):
        """`status` and `kind` had a default, so documents written before they were set
        carry the meaning of that default, not an unknown one."""
        pending = self.insert({"_cls": "ValidateHarvesterNotificationDetails", "source": None})
        request = self.insert({"_cls": "MembershipRequestNotificationDetails", "kind": None})

        self.run_migration()

        assert self.stored(pending)["type"] == NotificationType.HARVEST_SOURCE_PENDING
        assert self.stored(request)["type"] == NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED

    def test_an_undecidable_notification_is_left_untyped_rather_than_guessed(self):
        """Discussion and badge notifications have no default to fall back on: mapping
        them to an arbitrary type would show the user the wrong event."""
        unknown = self.insert({"_cls": "DiscussionNotificationDetails", "discussion": None})
        detail_less = self.insert(None)

        self.run_migration()

        assert "type" not in self.stored(unknown)
        assert self.stored(unknown)["details"] == {
            "_cls": "DiscussionNotificationDetails",
            "discussion": None,
        }
        assert "type" not in self.stored(detail_less)

    def test_running_it_twice_changes_nothing(self):
        notification = self.insert(
            {"_cls": "DiscussionNotificationDetails", "status": "new_comment"}
        )

        self.run_migration()
        first = self.stored(notification)
        self.run_migration()

        assert self.stored(notification) == first
