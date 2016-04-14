# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import MembershipRequest, Member

from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import (
    membership_request_notifications
)

from .. import TestCase, DBTestMixin


class OrganizationNotificationsTest(TestCase, DBTestMixin):
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

        self.assertEqual(len(membership_request_notifications(applicant)), 0)
        self.assertEqual(len(membership_request_notifications(editor)), 0)

        notifications = membership_request_notifications(admin)
        self.assertEqual(len(notifications), 1)
        dt, details = notifications[0]
        self.assertEqualDates(dt, request.created)
        self.assertEqual(details['id'], request.id)
        self.assertEqual(details['organization'], org.id)
        self.assertEqual(details['user']['id'], applicant.id)
        self.assertEqual(details['user']['fullname'], applicant.fullname)
        self.assertEqual(details['user']['avatar'], str(applicant.avatar))
