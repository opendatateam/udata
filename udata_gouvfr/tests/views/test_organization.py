import pytest

from flask import url_for

from udata.models import (
    Organization, Member, CERTIFIED, PUBLIC_SERVICE
)

from udata.core.badges.factories import badge_factory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory

from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory, AdminFactory

from udata.tests.helpers import capture_mails
from udata.tests.frontend import FrontTestCase
from udata.tests.helpers import capture_mails, assert_starts_with

from udata_gouvfr.tests import GouvFrSettings

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
]


class OrganizationBadgeAPITest:
    settings = GouvFrSettings
    modules = []

    @pytest.fixture(autouse=True)
    def setUp(self, api, clean_db):
        # Register at least two badges
        Organization.__badges__['test-1'] = 'Test 1'
        Organization.__badges__['test-2'] = 'Test 2'

        self.factory = badge_factory(Organization)
        self.user = api.login(AdminFactory())
        self.organization = OrganizationFactory()

    def test_create_badge_certified_mail(self, api):
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])

        data = self.factory.as_dict()
        data['kind'] = CERTIFIED

        with capture_mails() as mails:
            api.post(url_for('api.organization_badges', org=org), data)

        # Should have sent one mail to each member of organization
        members_emails = [m.user.email for m in org.members]
        assert len(mails) == len(members_emails)
        assert [m.recipients[0] for m in mails] == members_emails

    def test_create_badge_public_service_mail(self, api):
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])

        data = self.factory.as_dict()
        data['kind'] = PUBLIC_SERVICE

        with capture_mails() as mails:
            api.post(url_for('api.organization_badges', org=org), data)
            # do it a second time, no email expected for this one
            api.post(url_for('api.organization_badges', org=self.organization), data)

        # Should have sent one mail to each member of organization
        members_emails = [m.user.email for m in org.members]
        assert len(mails) == len(members_emails)
        assert [m.recipients[0] for m in mails] == members_emails


class DiscussionCsvTest(FrontTestCase):
    settings = GouvFrSettings
    modules = []

    def test_discussions_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(
            url_for('organizations.discussions_csv', org=organization))
        self.assert200(response)

        self.assertEqual(
            response.data.decode('utf8'),
            ('"id";"user";"subject";"title";"size";"messages";"created";'
             '"closed";"closed_by"\r\n')
        )

    def test_discussions_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name='John', last_name='Snow')
        discussion = DiscussionFactory(subject=dataset, user=user)
        response = self.get(
            url_for('organizations.discussions_csv', org=organization))
        self.assert200(response)

        headers, data = response.data.decode('utf-8').strip().split('\r\n')
        expected = '"{discussion.id}";"{discussion.user}"'
        assert_starts_with(data, expected.format(discussion=discussion))
