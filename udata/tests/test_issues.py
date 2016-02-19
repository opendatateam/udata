# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.models import db, Dataset, DatasetIssue, ReuseIssue, Member
from udata.core.user.views import blueprint as user_bp
from udata.core.issues.models import Issue, Message
from udata.core.issues.actions import issues_for
from udata.core.issues.notifications import issues_notifications
from udata.core.issues.signals import (
    on_new_issue, on_new_issue_comment, on_issue_closed
)

from frontend import FrontTestCase

from . import TestCase, DBTestMixin
from .api import APITestCase

from .factories import (
    faker, UserFactory, OrganizationFactory, DatasetFactory, ReuseFactory,
    DatasetIssueFactory
)


class IssuesTest(APITestCase):
    def create_app(self):
        app = super(IssuesTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_issue(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        with self.assert_emit(on_new_issue):
            response = self.post(url_for('api.issues', **{'for': dataset.id}), {
                'title': 'test title',
                'comment': 'bla bla',
                'subject': dataset.id
            })
        self.assertStatus(response, 201)

        dataset.reload()
        self.assertEqual(dataset.metrics['issues'], 1)

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
            'subject': dataset.id
        })
        self.assertStatus(response, 400)

    def test_new_issue_missing_title(self):
        self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.issues', **{'for': dataset.id}), {
            'comment': 'bla bla',
            'subject': dataset.id
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
            issue = DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message]
            )
            open_issues.append(issue)
        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        closed_issues = [DatasetIssue.objects.create(
            subject=dataset,
            user=user,
            title='test issue {}'.format(i),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )]

        response = self.get(url_for('api.issues', id=dataset.id))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), (len(open_issues) +
                                                      len(closed_issues)))

    def test_list_with_close_issues(self):
        dataset = Dataset.objects.create(title='Test dataset')
        open_issues = []
        closed_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message]
            )
            open_issues.append(issue)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title='test issue {}'.format(i),
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_issues.append(issue)

        response = self.get(url_for('api.issues', id=dataset.id, closed=True))
        self.assert200(response)

        self.assertEqual(len(response.json), len(open_issues + closed_issues))

    def test_get_issue(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = DatasetIssue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )

        response = self.get(url_for('api.issue', id=issue.id))
        self.assert200(response)

        data = response.json

        self.assertEqual(data['subject'], str(dataset.id))
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
        issue = DatasetIssue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )
        on_new_issue.send(issue)  # Updating metrics.

        poster = self.login()
        with self.assert_emit(on_new_issue_comment):
            response = self.post(url_for('api.issue', id=issue.id), {
                'comment': 'new bla bla'
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.metrics['issues'], 1)

        data = response.json

        self.assertEqual(data['subject'], str(dataset.id))
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
        issue = DatasetIssue.objects.create(
            subject=dataset,
            user=user,
            title='test issue',
            discussion=[message]
        )
        on_new_issue.send(issue)  # Updating metrics.

        with self.assert_emit(on_issue_closed):
            response = self.post(url_for('api.issue', id=issue.id), {
                'comment': 'close bla bla',
                'close': True
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.metrics['issues'], 0)

        data = response.json

        self.assertEqual(data['subject'], str(dataset.id))
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
        issue = DatasetIssue.objects.create(
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
        self.assertEqual(dataset.metrics['issues'], 1)

    def test_list_issues_filter_closed(self):
        '''Should consider the closed filtering on issues'''
        user = UserFactory()
        dataset = DatasetFactory()
        (issue,) = DatasetIssue.objects.create(subject=dataset, title='',
                                               user=user),
        (issue_closed,) = DatasetIssue.objects.create(subject=dataset,
            title='', closed=datetime.now(), user=user),

        response_all = self.get(url_for('api.issues'))
        self.assert200(response_all)

        data_all = response_all.json['data']
        self.assertEqual(len(data_all), 2)
        self.assertItemsEqual([str(issue.id), str(issue_closed.id)],
                              [str(d['id']) for d in data_all])

        response_closed = self.get(url_for('api.issues', closed=True))
        self.assert200(response_closed)
        data_closed = response_closed.json['data']
        self.assertEqual(len(data_closed), 1)
        self.assertEqual(str(issue_closed.id), data_closed[0]['id'])

        response_open = self.get(url_for('api.issues', closed=False))
        self.assert200(response_open)
        data_open = response_open.json['data']
        self.assertEqual(len(data_open), 1)

        self.assertEqual(str(issue.id), data_open[0]['id'])


class IssueCsvTest(FrontTestCase):

    def test_issues_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(
            url_for('organizations.issues_csv', org=organization))
        self.assert200(response)

        self.assertEqual(
            response.data,
            ('"id";"user";"subject";"title";"size";"messages";"created";'
             '"closed";"closed_by"\r\n')
        )

    def test_issues_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name='John', last_name='Snow')
        issue = DatasetIssueFactory(subject=dataset, user=user)
        response = self.get(
            url_for('organizations.issues_csv', org=organization))
        self.assert200(response)

        headers, data = response.data.strip().split('\r\n')
        self.assertStartswith(
            data, '"{issue.id}";"{issue.user}"'.format(issue=issue))


class IssuesActionsTest(TestCase, DBTestMixin):
    def test_issues_for_user(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(owner=owner)

        open_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            open_issues.append(DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))
            open_issues.append(ReuseIssue.objects.create(
                subject=reuse,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))

        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        DatasetIssue.objects.create(
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
            open_issues.append(DatasetIssue.objects.create(
                subject=dataset,
                user=sender,
                title=faker.sentence(),
                discussion=[message]
            ))
            open_issues.append(ReuseIssue.objects.create(
                subject=reuse,
                user=sender,
                title=faker.sentence(),
                discussion=[message]
            ))
        # Creating a closed issue that shouldn't show up in response.
        other_user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=other_user)
        DatasetIssue.objects.create(
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
            open_issues.append(DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))
            open_issues.append(ReuseIssue.objects.create(
                subject=reuse,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            ))

        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        DatasetIssue.objects.create(
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
            issue = DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_issues[issue.id] = issue

        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        DatasetIssue.objects.create(
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
            issue = DatasetIssue.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_issues[issue.id] = issue
        # Creating a closed issue that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        DatasetIssue.objects.create(
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
