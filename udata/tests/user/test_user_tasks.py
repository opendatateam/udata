from datetime import datetime, timedelta

import pytest
from flask import current_app

from udata.core.discussions.factories import DiscussionFactory
from udata.core.user import tasks
from udata.core.user.factories import UserFactory
from udata.core.user.models import User
from udata.i18n import gettext as _
from udata.tests.api import APITestCase
from udata.tests.helpers import capture_mails


class UserTasksTest(APITestCase):
    @pytest.mark.options(YEARS_OF_INACTIVITY_BEFORE_DELETION=3)
    def test_notify_inactive_users(self):
        notification_comparison_date = (
            datetime.utcnow()
            - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365)
            + timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
            - timedelta(days=1)  # add margin
        )

        inactive_user = UserFactory(current_login_at=notification_comparison_date)
        UserFactory(current_login_at=datetime.utcnow())  # Active user

        with capture_mails() as mails:
            tasks.notify_inactive_users()

        # Assert (only one) mail has been sent
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].send_to, set([inactive_user.email]))
        self.assertEqual(
            mails[0].subject,
            _("Inactivity of your {site} account").format(site=current_app.config["SITE_TITLE"]),
        )

        # We shouldn't notify users twice
        with capture_mails() as mails:
            tasks.notify_inactive_users()

        self.assertEqual(len(mails), 0)

    @pytest.mark.options(YEARS_OF_INACTIVITY_BEFORE_DELETION=3)
    @pytest.mark.options(MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS=10)
    def test_notify_inactive_users_max_notifications(self):
        notification_comparison_date = (
            datetime.utcnow()
            - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365)
            + timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
            - timedelta(days=1)  # add margin
        )

        NB_USERS_TO_NOTIFY = 15

        [UserFactory(current_login_at=notification_comparison_date) for _ in range(15)]
        UserFactory(current_login_at=datetime.utcnow())  # Active user

        with capture_mails() as mails:
            tasks.notify_inactive_users()

        # Assert MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS mails have been sent
        self.assertEqual(
            len(mails), current_app.config["MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS"]
        )

        # Second batch
        with capture_mails() as mails:
            tasks.notify_inactive_users()

        # Assert what's left have been sent
        self.assertEqual(
            len(mails),
            NB_USERS_TO_NOTIFY - current_app.config["MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS"],
        )

    @pytest.mark.options(YEARS_OF_INACTIVITY_BEFORE_DELETION=3)
    def test_delete_inactive_users(self):
        deletion_comparison_date = (
            datetime.utcnow()
            - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365)
            - timedelta(days=1)  # add margin
        )

        notification_comparison_date = (
            datetime.utcnow()
            - timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
            - timedelta(days=1)  # add margin
        )

        inactive_user_to_delete = UserFactory(
            current_login_at=deletion_comparison_date,
            inactive_deletion_notified_at=notification_comparison_date,
        )
        UserFactory(current_login_at=datetime.utcnow())  # Active user
        discussion = DiscussionFactory(user=inactive_user_to_delete)
        discussion_title = discussion.title

        with capture_mails() as mails:
            tasks.delete_inactive_users()

        # Assert (only one) mail has been sent
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].send_to, set([inactive_user_to_delete.email]))
        self.assertEqual(
            mails[0].subject,
            _(
                _("Deletion of your inactive {site} account").format(
                    site=current_app.config["SITE_TITLE"]
                )
            ),
        )

        # Assert user has been deleted but not its discussion
        inactive_user_to_delete.reload()
        discussion.reload()
        self.assertEqual(inactive_user_to_delete.fullname, "DELETED DELETED")
        self.assertEqual(discussion.title, discussion_title)

    @pytest.mark.options(YEARS_OF_INACTIVITY_BEFORE_DELETION=3)
    def test_keep_inactive_users_that_logged_in(self):
        notification_comparison_date = (
            datetime.utcnow()
            - timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
            - timedelta(days=1)  # add margin
        )

        inactive_user_that_logged_in_since_notification = UserFactory(
            current_login_at=datetime.utcnow(),
            inactive_deletion_notified_at=notification_comparison_date,
        )

        with capture_mails() as mails:
            tasks.delete_inactive_users()

        # Assert no mail has been sent
        self.assertEqual(len(mails), 0)

        # Assert user hasn't been deleted and won't be deleted
        self.assertEqual(User.objects().count(), 1)
        user = User.objects().first()
        self.assertEqual(user, inactive_user_that_logged_in_since_notification)
        self.assertIsNone(user.inactive_deletion_notified_at)
