from datetime import datetime, timedelta

import pytest
from flask import current_app

from udata.core.organization.models import Member, MembershipRequest, Organization
from udata.core.user.factories import UserFactory
from udata.features.notifications import tasks
from udata.features.notifications.models import Notification
from udata.tests.api import APITestCase


class UserTasksTest(APITestCase):
    @pytest.mark.options(DAYS_AFTER_NOTIFICATION_EXPIRED=3)
    def test_notify_inactive_users(self):
        self.login()
        member = Member(user=self.user, role="admin")
        org = Organization.objects.create(
            name="with transfert", description="XXX", members=[member]
        )

        notification_handled_date = (
            datetime.utcnow()
            - timedelta(days=current_app.config["DAYS_AFTER_NOTIFICATION_EXPIRED"])
            - timedelta(days=1)  # add margin
        )

        applicant = UserFactory()

        request = MembershipRequest(user=applicant, comment="test")
        org.add_membership_request(request)

        assert Notification.objects.count() == 1

        request.status = "accepted"
        request.handled_by = self.user
        request.handled_on = notification_handled_date
        org.save()
        MembershipRequest.after_handle.send(request, org=org)

        tasks.delete_expired_notifications()

        assert Notification.objects.count() == 0
