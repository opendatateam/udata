# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.models import Dataset, DatasetIssue
from udata.core.user.views import blueprint as user_bp
from udata.core.issues.models import Issue, Message
from udata.core.issues.signals import on_new_issue

from frontend import FrontTestCase

from .api import APITestCase
from .factories import (
    faker, UserFactory, OrganizationFactory, DatasetFactory, DatasetIssueFactory
)


class IssuesTest(APITestCase):
    def create_app(self):
        app = super(IssuesTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_issue(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset')

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
        issue = DatasetIssue.objects.create(
            subject=dataset,
            user=user,
            title='test issue {}'.format(i),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        response = self.get(url_for('api.issues', id=dataset.id))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(open_issues))

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
        self.assertEqual(data['discussion'][0]['posted_by']['id'], str(user.id))
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
        self.assertEqual(data['discussion'][1]['posted_by']['id'], str(poster.id))
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
        self.assertEqual(data['discussion'][1]['posted_by']['id'], str(owner.id))
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


class IssueCsvTest(FrontTestCase):

    def test_issues_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(url_for('organizations.issues_csv', org=organization))
        self.assert200(response)

        self.assertEqual(
            response.data,
            '"id";"user";"subject";"title";"size";"messages";"created";"closed";"closed_by"\r\n'
        )

    def test_issues_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name='John', last_name='Snow')
        issue = DatasetIssueFactory(subject=dataset, user=user)
        response = self.get(url_for('organizations.issues_csv', org=organization))
        self.assert200(response)

        headers, data = response.data.strip().split('\r\n')
        self.assertStartswith(data, '"{issue.id}";"{issue.user}"'.format(issue=issue))
