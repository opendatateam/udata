from flask import url_for

from udata.core.issues.models import Issue, Message
from udata.core.issues.factories import IssueFactory
from udata.core.issues.signals import (  # noqa
    on_new_issue, on_new_issue_comment, on_issue_closed
)
from udata.core.issues.tasks import (
    notify_new_issue, notify_new_issue_comment, notify_issue_closed
)
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata.utils import faker
from udata.tests.helpers import capture_mails, assert_starts_with
from udata_gouvfr.tests import GouvFrSettings
from udata_gouvfr.tests.frontend import GouvfrFrontTestCase


class IssuesMailsTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = []

    def test_new_issue_mail(self):
        user = UserFactory()
        owner = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        issue = Issue.objects.create(
            subject=DatasetFactory(owner=owner),
            user=user,
            title=faker.sentence(),
            discussion=[message]
        )

        with capture_mails() as mails:
            notify_new_issue(issue.id)

        # Should have sent one mail to the owner
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].recipients[0], owner.email)

    def test_new_issue_comment_mail(self):
        owner = UserFactory()
        poster = UserFactory()
        commenter = UserFactory()
        message = Message(content=faker.sentence(), posted_by=poster)
        new_message = Message(content=faker.sentence(), posted_by=commenter)
        issue = Issue.objects.create(
            subject=DatasetFactory(owner=owner),
            user=poster,
            title=faker.sentence(),
            discussion=[message, new_message]
        )

        # issue = IssueFactory()
        with capture_mails() as mails:
            notify_new_issue_comment(issue.id, message=len(issue.discussion) - 1)

        # Should have sent one mail to the owner and the other participants
        # and no mail to the commenter
        expected_recipients = (owner.email, poster.email)
        self.assertEqual(len(mails), len(expected_recipients))
        for mail in mails:
            self.assertIn(mail.recipients[0], expected_recipients)
            self.assertNotIn(commenter.email, mail.recipients)

    def test_closed_issue_mail(self):
        owner = UserFactory()
        poster = UserFactory()
        commenter = UserFactory()
        message = Message(content=faker.sentence(), posted_by=poster)
        second_message = Message(content=faker.sentence(), posted_by=commenter)
        closing_message = Message(content=faker.sentence(), posted_by=owner)
        issue = Issue.objects.create(
            subject=DatasetFactory(owner=owner),
            user=poster,
            title=faker.sentence(),
            discussion=[message, second_message, closing_message]
        )

        # issue = IssueFactory()
        with capture_mails() as mails:
            notify_issue_closed(issue.id, message=len(issue.discussion) - 1)

        # Should have sent one mail to each participant
        # and no mail to the closer
        expected_recipients = (poster.email, commenter.email)
        self.assertEqual(len(mails), len(expected_recipients))
        for mail in mails:
            self.assertIn(mail.recipients[0], expected_recipients)
            self.assertNotIn(owner.email, mail.recipients)


class IssueCsvTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = []

    def test_issues_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(
            url_for('organizations.issues_csv', org=organization))
        self.assert200(response)

        self.assertEqual(
            response.data.decode('utf8').strip(),
            ('"id";"user";"subject";"title";"size";"messages";"created";'
             '"closed";"closed_by"')
        )

    def test_issues_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name='John', last_name='Snow')
        issue = IssueFactory(subject=dataset, user=user)
        response = self.get(
            url_for('organizations.issues_csv', org=organization))
        self.assert200(response)

        headers, data = response.data.decode('utf-8').strip().split('\r\n')
        expected = '"{issue.id}";"{issue.user}"'.format(issue=issue)
        assert_starts_with(data, expected)
