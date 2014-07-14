# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for, Blueprint

from udata.api import api
from udata.models import db

from udata.core.metrics.models import WithMetrics
from udata.core.user.views import blueprint as user_bp

from udata.core.issues.models import Issue, Message, ISSUE_TYPES
from udata.core.issues.metrics import IssuesMetric
from udata.core.issues.api import IssuesAPI, IssueAPI

from .api import APITestCase
from .factories import faker, UserFactory


bp = Blueprint('test_issues', __name__)


class Fake(WithMetrics, db.Document):
    name = db.StringField()


class FakeIssue(Issue):
    subject = db.ReferenceField(Fake)


class FakeIssuesMetric(IssuesMetric):
    model = Fake


class FakeIssuesAPI(IssuesAPI):
    model = FakeIssue


class FakeIssueAPI(IssueAPI):
    model = FakeIssue


api.add_resource(FakeIssuesAPI, '/test/<id>/issues/', endpoint=b'api.fake_issues')


class IssuesTest(APITestCase):
    def create_app(self):
        app = super(IssuesTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_issue(self):
        user = self.login()
        fake = Fake.objects.create(name='Fake')

        response = self.post(url_for('api.fake_issues', id=fake.id), {
            'type': 'other',
            'comment': 'bla bla'
        })
        self.assertStatus(response, 201)

        fake.reload()
        self.assertEqual(fake.metrics['issues'], 1)

        issues = Issue.objects(subject=fake)
        self.assertEqual(len(issues), 1)

        issue = issues[0]
        self.assertEqual(issue.type, 'other')
        self.assertEqual(issue.user, user)
        self.assertEqual(len(issue.discussion), 1)
        self.assertIsNotNone(issue.created)
        self.assertIsNone(issue.closed)
        self.assertIsNone(issue.closed_by)

        message = issue.discussion[0]
        self.assertEqual(message.content, 'bla bla')
        self.assertEqual(message.posted_by, user)
        self.assertIsNotNone(message.posted_on)

    def test_new_issue_missing_comment(self):
        self.login()
        fake = Fake.objects.create(name='Fake')

        response = self.post(url_for('api.fake_issues', id=fake.id), {
            'type': 'other'
        })
        self.assertStatus(response, 400)

    def test_new_issue_missing_type(self):
        self.login()
        fake = Fake.objects.create(name='Fake')

        response = self.post(url_for('api.fake_issues', id=fake.id), {
            'comment': 'bla bla'
        })
        self.assertStatus(response, 400)

    def test_list_issues(self):
        fake = Fake.objects.create()
        open_issues = []
        # closed_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = FakeIssue.objects.create(
                subject=fake,
                type=ISSUE_TYPES.keys()[i],
                user=user,
                discussion=[message]
            )
            open_issues.append(issue)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = FakeIssue.objects.create(
                subject=fake,
                type=ISSUE_TYPES.keys()[i],
                user=user,
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            # closed_issues.append(issue)

        response = self.get(url_for('api.fake_issues', id=fake.id))
        self.assert200(response)

        self.assertEqual(len(response.json), len(open_issues))

    def test_list_with_close_issues(self):
        fake = Fake.objects.create()
        open_issues = []
        closed_issues = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = FakeIssue.objects.create(
                subject=fake,
                type=ISSUE_TYPES.keys()[i],
                user=user,
                discussion=[message]
            )
            open_issues.append(issue)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            issue = FakeIssue.objects.create(
                subject=fake,
                type=ISSUE_TYPES.keys()[i],
                user=user,
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_issues.append(issue)


        response = self.get(url_for('api.fake_issues', id=fake.id, closed=True))
        self.assert200(response)

        self.assertEqual(len(response.json), len(open_issues + closed_issues))

    def test_get_issue(self):
        fake = Fake.objects.create()
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = FakeIssue.objects.create(
            subject=fake,
            type='other',
            user=user,
            discussion=[message]
        )

        response = self.get(url_for('api.issue', id=issue.id))
        self.assert200(response)

        data = response.json

        self.assertEqual(data['type'], 'other')
        self.assertEqual(data['subject'], str(fake.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertIsNotNone(data['created'])
        self.assertEqual(len(data['discussion']), 1)
        self.assertEqual(data['discussion'][0]['content'], 'bla bla')
        self.assertEqual(data['discussion'][0]['posted_by']['id'], str(user.id))
        self.assertIsNotNone(data['discussion'][0]['posted_on'])

    def test_add_comment_to_issue(self):
        fake = Fake.objects.create(metrics={'issues': 1})
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = FakeIssue.objects.create(
            subject=fake,
            type='other',
            user=user,
            discussion=[message]
        )

        poster = self.login()
        response = self.post(url_for('api.issue', id=issue.id), {
            'comment': 'new bla bla'
        })
        self.assert200(response)

        fake.reload()
        self.assertEqual(fake.metrics['issues'], 1)

        data = response.json

        self.assertEqual(data['type'], 'other')
        self.assertEqual(data['subject'], str(fake.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertIsNotNone(data['created'])
        self.assertIsNone(data['closed'])
        self.assertIsNone(data['closed_by'])
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'new bla bla')
        self.assertEqual(data['discussion'][1]['posted_by']['id'], str(poster.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_issue(self):
        fake = Fake.objects.create(metrics={'issues': 1})
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        issue = FakeIssue.objects.create(
            subject=fake,
            type='other',
            user=user,
            discussion=[message]
        )

        closer = self.login()
        response = self.post(url_for('api.issue', id=issue.id), {
            'comment': 'close bla bla',
            'close': True
        })
        self.assert200(response)

        fake.reload()
        self.assertEqual(fake.metrics['issues'], 0)

        data = response.json

        self.assertEqual(data['type'], 'other')
        self.assertEqual(data['subject'], str(fake.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertIsNotNone(data['created'])
        self.assertIsNotNone(data['closed'])
        self.assertEqual(data['closed_by'], str(closer.id))
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'close bla bla')
        self.assertEqual(data['discussion'][1]['posted_by']['id'], str(closer.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])
