import pytest

from udata.models import MembershipRequest, Member

from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import (
    membership_request_notifications
)

from udata.tests.helpers import assert_equal_dates


@pytest.mark.usefixtures('clean_db')
class OrganizationNotificationsTest:
    def test_pending_membership_requests(self):
        admin = UserFactory()
        editor = UserFactory()
        applicant = UserFactory()
        request = MembershipRequest(user=applicant, comment='test')
        members = [
            Member(user=editor, role='editor'),
            Member(user=admin, role='admin')
        ]
        org = OrganizationFactory(members=members, requests=[request])

        assert len(membership_request_notifications(applicant)) is 0
        assert len(membership_request_notifications(editor)) is 0

        notifications = membership_request_notifications(admin)
        assert len(notifications) is 1
        dt, details = notifications[0]
        assert_equal_dates(dt, request.created)
        assert details['id'] == request.id
        assert details['organization'] == org.id
        assert details['user']['id'] == applicant.id
        assert details['user']['fullname'] == applicant.fullname
        assert details['user']['avatar'] == str(applicant.avatar)
