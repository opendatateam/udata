from datetime import datetime

from flask import url_for

from udata.models import db, Dataset, Member
from udata.core.issues.models import Issue, Message
from udata.core.issues.metrics import update_issues_metric
from udata.core.issues.actions import issues_for
from udata.core.issues.notifications import issues_notifications
from udata.core.issues.signals import (
    on_new_issue, on_new_issue_comment, on_issue_closed
)
from udata.core.issues.tasks import (
    notify_new_issue, notify_new_issue_comment, notify_issue_closed
)
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.utils import faker


from . import TestCase, DBTestMixin
from .api import APITestCase
from .helpers import assert_emit


class IssuesTest(APITestCase):
    modules = []

    def test_new_issue(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        url = url_for('api.issues', **{'for': dataset.id})
        with assert_emit(on_new_issue):
            response = self.post(url, {
                'title': 'test title',
                'comment': 'bla bla',
                'subject': {
                    'class': 'Dataset',
                    'id': dataset.id,
                }
            })
        self.assert201(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()['issues'], 1)

        issues = Issue.objects(subject=dataset)
        self.assertEqual(len(issues), 1)

        issue = issues[0]
        self.assertEqual(issue.user, user)
        self.assertEqual(len(issue.discussion), 1)
        self.assertIsNotNone(issue.created)
        self.assertIsNone(issue.closed)
        self.assertIsNone(issue.closed_by)
        self.assertEqual(issue.title, 'test title')

        message = issue.discussion[0]
        self.assertEqual(message.content, 'bla bla')
        self.assertEqual(message.posted_by, user)
        self.assertIsNotNone(message.posted_on)

    def test_new_issue_missing_comment(self):
        self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.issues', **{'for': dataset.id}), {
            'title': 'test title',
            'subject': {
                'class': 'Dataset',
                'id': dataset.id,
            }
        })
        self.assertStatus(response, 400)

    def test_new_issue_missing_title(self):
        self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.issues', **{'for': dataset.id}), {
            'comment': 'bla bla',
            'subject': {
                'class': 'Dataset',
                'id': dataset.id,
            }
        })
        self.assertStatus(response, 400)

    def test_new_issue_missing_subject(self):
        self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.issues', **{'for': dataset.id}), {
            'title': 'test title',
            'comment': 'bla bla'
        })
        self.assertStatus(response, 400)

    def test_list_issues(self):
        dataset = Dataset.objects.create(title='Test dataset')
        open_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = Issue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message]
            )
            open_issues.append(issue)
        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        closed_issues = [Issue.objects.create(
            subject=dataset,
            user=user,
            title='test issue {}'.format(i),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )]

        response = self.get(url_for('api.issues'))
        self.assert200(response)
        expected_length = len(open_issues + closed_issues)
        self.assertEqual(len(response.json['data']), expected_length)

    def test_list_issues_closed_filter(self):
        dataset = Dataset.objects.create(title='Test dataset')
        open_issues = []
        closed_issues = []
        for i in range(2):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = Issue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message]
            )
            open_issues.append(issue)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = Issue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_issues.append(issue)

        response = self.get(url_for('api.issues', closed=True))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(closed_issues))
        for issue in response.json['data']:
            self.assertIsNotNone(issue['closed'])

        response = self.get(url_for('api.issues', id=dataset.id, closed=False))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(open_issues))
        for issue in response.json['data']:
            self.assertIsNone(issue['closed'])

    def test_list_issues_for(self):
        dataset = Dataset.objects.create(title='Test dataset')
        issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = Issue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message]
            )
            issues.append(issue)
        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        other_dataset = Dataset.objects.create(title='Other Test dataset')
        message = Message(content=faker.sentence(), posted_by=user)
        issue = Issue.objects.create(
            subject=other_dataset,
            user=user,
            title='test issue {}'.format(i),
            discussion=[message]
        )

        kwargs = {'for': str(dataset.id)}
        response = self.get(url_for('api.issues', **kwargs))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(issues))

    def test_get_issue(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = Issue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )

        response = self.get(url_for('api.issue', id=issue.id))
        self.assert200(response)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test issue')
        self.assertIsNotNone(data['created'])
        self.assertEqual(len(data['discussion']), 1)
        self.assertEqual(data['discussion'][0]['content'], 'bla bla')
        self.assertEqual(data['discussion'][0]['posted_by']['id'],
                         str(user.id))
        self.assertIsNotNone(data['discussion'][0]['posted_on'])

    def test_add_comment_to_issue(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = Issue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )

        on_new_issue.send(issue)  # Updating metrics.
        poster = self.login()
        with assert_emit(on_new_issue_comment):
            response = self.post(url_for('api.issue', id=issue.id), {
                'comment': 'new bla bla'
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()['issues'], 1)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test issue')
        self.assertIsNotNone(data['created'])
        self.assertIsNone(data['closed'])
        self.assertIsNone(data['closed_by'])
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'new bla bla')
        self.assertEqual(data['discussion'][1]['posted_by']['id'],
                         str(poster.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_issue(self):
        owner = self.login()
        user = UserFactory()
        dataset = Dataset.objects.create(title='Test dataset', owner=owner)
        message = Message(content='bla bla', posted_by=user)
        issue = Issue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )
        on_new_issue.send(issue)  # Updating metrics.

        with assert_emit(on_issue_closed):
            response = self.post(url_for('api.issue', id=issue.id), {
                'comment': 'close bla bla',
                'close': True
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()['issues'], 0)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test issue')
        self.assertIsNotNone(data['created'])
        self.assertIsNotNone(data['closed'])
        self.assertEqual(data['closed_by'], str(owner.id))
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'close bla bla')
        self.assertEqual(data['discussion'][1]['posted_by']['id'],
                         str(owner.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_issue_permissions(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = Issue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )
        on_new_issue.send(issue)  # Updating metrics.

        self.login()
        response = self.post(url_for('api.issue', id=issue.id), {
            'comment': 'close bla bla',
            'close': True
        })
        self.assert403(response)

        dataset.reload()
        # Metrics unchanged after attempt to close the discussion.
        self.assertEqual(dataset.get_metrics()['issues'], 1)


class IssuesActionsTest(TestCase, DBTestMixin):
    def test_issues_for_user(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(owner=owner)

        open_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            open_issues.append(Issue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))
            open_issues.append(Issue.objects.create(
                subject=reuse,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))

        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Issue.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        issues = issues_for(owner)

        self.assertIsInstance(issues, db.BaseQuerySet)
        self.assertEqual(len(issues), len(open_issues))

        for issue in issues:
            self.assertIn(issue, open_issues)

    def test_issues_for_user_with_org(self):
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(organization=org)
        reuse = ReuseFactory(organization=org)

        open_issues = []
        for i in range(3):
            sender = UserFactory()
            message = Message(content=faker.sentence(), posted_by=sender)
            open_issues.append(Issue.objects.create(
                subject=dataset,
                user=sender,
                title=faker.sentence(),
                discussion=[message]
            ))
            open_issues.append(Issue.objects.create(
                subject=reuse,
                user=sender,
                title=faker.sentence(),
                discussion=[message]
            ))
        # Creating a closed issue that shouldn't show up in response.
        other_user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=other_user)
        Issue.objects.create(
            subject=dataset,
            user=other_user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        issues = issues_for(user)

        self.assertIsInstance(issues, db.BaseQuerySet)
        self.assertEqual(len(issues), len(open_issues))

        for issue in issues:
            self.assertIn(issue, open_issues)

    def test_issues_for_user_with_closed(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(owner=owner)

        open_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            open_issues.append(Issue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))
            open_issues.append(Issue.objects.create(
                subject=reuse,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))

        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Issue.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        issues = issues_for(owner, only_open=False)

        self.assertEqual(len(issues), len(open_issues) + 1)


class IssuesNotificationsTest(TestCase, DBTestMixin):
    def test_notify_user_issues(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        open_issues = {}
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = Issue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_issues[issue.id] = issue

        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Issue.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        notifications = issues_notifications(owner)

        self.assertEqual(len(notifications), len(open_issues))

        for dt, details in notifications:
            issue = open_issues[details['id']]
            self.assertEqual(details['title'], issue.title)
            self.assertEqual(details['subject']['id'], issue.subject.id)
            self.assertEqual(details['subject']['type'], 'dataset')

    def test_notify_org_issues(self):
        recipient = UserFactory()
        member = Member(user=recipient, role='editor')
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(organization=org)

        open_issues = {}
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = Issue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_issues[issue.id] = issue
        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Issue.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        notifications = issues_notifications(recipient)

        self.assertEqual(len(notifications), len(open_issues))

        for dt, details in notifications:
            issue = open_issues[details['id']]
            self.assertEqual(details['title'], issue.title)
            self.assertEqual(details['subject']['id'], issue.subject.id)
            self.assertEqual(details['subject']['type'], 'dataset')
