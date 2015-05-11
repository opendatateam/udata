# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for, Blueprint

from udata.api import api
from udata.models import db

from udata.core.metrics.models import WithMetrics
from udata.core.user.views import blueprint as user_bp

from udata.core.discussions.models import Discussion, Message
from udata.core.discussions.metrics import DiscussionsMetric
from udata.core.discussions.api import DiscussionsAPI

from .api import APITestCase
from .factories import faker, UserFactory


bp = Blueprint('test_discussions', __name__)
ns = api.namespace('test', 'A test namespace')


class Fake(WithMetrics, db.Document):
    name = db.StringField()
    owner = db.ReferenceField('User')
    organization = db.ReferenceField('Organization')


class FakeDiscussion(Discussion):
    subject = db.ReferenceField(Fake)


class FakeDiscussionsMetric(DiscussionsMetric):
    model = Fake


@ns.route('/discussions/', endpoint='fake_discussions')
class FakeDiscussionsAPI(DiscussionsAPI):
    model = FakeDiscussion


class DiscussionsTest(APITestCase):
    def create_app(self):
        app = super(DiscussionsTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_discussion(self):
        user = self.login()
        fake = Fake.objects.create(name='Fake')

        response = self.post(url_for('api.fake_discussions', **{'for': fake.id}), {
            'title': 'test title',
            'comment': 'bla bla'
        })
        self.assertStatus(response, 201)

        fake.reload()
        self.assertEqual(fake.metrics['discussions'], 1)

        discussions = Discussion.objects(subject=fake)
        self.assertEqual(len(discussions), 1)

        discussion = discussions[0]
        self.assertEqual(discussion.user, user)
        self.assertEqual(len(discussion.discussion), 1)
        self.assertIsNotNone(discussion.created)
        self.assertIsNone(discussion.closed)
        self.assertIsNone(discussion.closed_by)
        self.assertEqual(discussion.title, 'test title')

        message = discussion.discussion[0]
        self.assertEqual(message.content, 'bla bla')
        self.assertEqual(message.posted_by, user)
        self.assertIsNotNone(message.posted_on)

    def test_new_discussion_missing_comment(self):
        self.login()
        fake = Fake.objects.create(name='Fake')

        response = self.post(url_for('api.fake_discussions', **{'for': fake.id}), {
            'title': 'test title'
        })
        self.assertStatus(response, 400)

    def test_new_discussion_missing_title(self):
        self.login()
        fake = Fake.objects.create(name='Fake')

        response = self.post(url_for('api.fake_discussions', **{'for': fake.id}), {
            'comment': 'bla bla'
        })
        self.assertStatus(response, 400)

    def test_list_discussions(self):
        fake = Fake.objects.create()
        open_discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = FakeDiscussion.objects.create(
                subject=fake,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            open_discussions.append(discussion)
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = FakeDiscussion.objects.create(
            subject=fake,
            user=user,
            title='test discussion {}'.format(i),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        response = self.get(url_for('api.fake_discussions', id=fake.id))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(open_discussions))

    def test_list_with_close_discussions(self):
        fake = Fake.objects.create()
        open_discussions = []
        closed_discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = FakeDiscussion.objects.create(
                subject=fake,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            open_discussions.append(discussion)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = FakeDiscussion.objects.create(
                subject=fake,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_discussions.append(discussion)

        response = self.get(url_for('api.fake_discussions', id=fake.id, closed=True))
        self.assert200(response)

        self.assertEqual(len(response.json), len(open_discussions + closed_discussions))

    def test_get_discussion(self):
        fake = Fake.objects.create()
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = FakeDiscussion.objects.create(
            subject=fake,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        response = self.get(url_for('api.discussion', id=discussion.id))
        self.assert200(response)

        data = response.json

        self.assertEqual(data['subject'], str(fake.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertEqual(len(data['discussion']), 1)
        self.assertEqual(data['discussion'][0]['content'], 'bla bla')
        self.assertEqual(data['discussion'][0]['posted_by']['id'], str(user.id))
        self.assertIsNotNone(data['discussion'][0]['posted_on'])

    def test_add_comment_to_discussion(self):
        fake = Fake.objects.create(metrics={'discussions': 1})
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = FakeDiscussion.objects.create(
            subject=fake,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        poster = self.login()
        response = self.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'new bla bla'
        })
        self.assert200(response)

        fake.reload()
        self.assertEqual(fake.metrics['discussions'], 1)

        data = response.json

        self.assertEqual(data['subject'], str(fake.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertIsNone(data['closed'])
        self.assertIsNone(data['closed_by'])
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'new bla bla')
        self.assertEqual(data['discussion'][1]['posted_by']['id'], str(poster.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_discussion(self):
        owner = self.login()
        user = UserFactory()
        fake = Fake.objects.create(metrics={'discussions': 1}, owner=owner)
        message = Message(content='bla bla', posted_by=user)
        discussion = FakeDiscussion.objects.create(
            subject=fake,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        response = self.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'close bla bla',
            'close': True
        })
        self.assert200(response)

        fake.reload()
        self.assertEqual(fake.metrics['discussions'], 0)

        data = response.json

        self.assertEqual(data['subject'], str(fake.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertIsNotNone(data['closed'])
        self.assertEqual(data['closed_by'], str(owner.id))
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'close bla bla')
        self.assertEqual(data['discussion'][1]['posted_by']['id'], str(owner.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_discussion_permissions(self):
        fake = Fake.objects.create(metrics={'discussions': 1})
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = FakeDiscussion.objects.create(
            subject=fake,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        self.login()
        response = self.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'close bla bla',
            'close': True
        })
        self.assert403(response)

        fake.reload()
        self.assertEqual(fake.metrics['discussions'], 1)
