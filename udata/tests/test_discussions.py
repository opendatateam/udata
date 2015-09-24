# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.models import Dataset, DatasetDiscussion, Member
from udata.core.user.views import blueprint as user_bp
from udata.core.discussions.models import Message, Discussion
from udata.core.discussions.notifications import discussions_notifications
from udata.core.discussions.signals import on_new_discussion

from frontend import FrontTestCase

from . import TestCase, DBTestMixin
from .api import APITestCase
from .factories import (
    faker, AdminFactory, UserFactory, OrganizationFactory, DatasetFactory,
    DatasetDiscussionFactory
)


class DiscussionsTest(APITestCase):
    def create_app(self):
        app = super(DiscussionsTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_discussion(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.discussions'), {
            'title': 'test title',
            'comment': 'bla bla',
            'subject': dataset.id
        })
        self.assertStatus(response, 201)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 1)

        discussions = Discussion.objects(subject=dataset)
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
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.discussions'), {
            'title': 'test title',
            'subject': dataset.id
        })
        self.assertStatus(response, 400)

    def test_new_discussion_missing_title(self):
        self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.discussions'), {
            'comment': 'bla bla',
            'subject': dataset.id
        })
        self.assertStatus(response, 400)

    def test_new_discussion_missing_subject(self):
        self.login()
        response = self.post(url_for('api.discussions'), {
            'title': 'test title',
            'comment': 'bla bla'
        })
        self.assertStatus(response, 400)

    def test_list_discussions(self):
        dataset = Dataset.objects.create(title='Test dataset')
        open_discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset.id,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            open_discussions.append(discussion)
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion {}'.format(i),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        response = self.get(url_for('api.discussions'))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(open_discussions))

    def test_list_with_close_discussions(self):
        dataset = Dataset.objects.create(title='Test dataset')
        open_discussions = []
        closed_discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset.id,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            open_discussions.append(discussion)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset.id,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_discussions.append(discussion)

        response = self.get(url_for('api.discussions', closed=True))
        self.assert200(response)

        self.assertEqual(len(response.json),
                         len(open_discussions + closed_discussions))

    def test_get_discussion(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        response = self.get(url_for('api.discussion', **{'id': discussion.id}))
        self.assert200(response)

        data = response.json

        self.assertEqual(data['subject'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertEqual(len(data['discussion']), 1)
        self.assertEqual(data['discussion'][0]['content'], 'bla bla')
        self.assertEqual(
            data['discussion'][0]['posted_by']['id'], str(user.id))
        self.assertIsNotNone(data['discussion'][0]['posted_on'])

    def test_add_comment_to_discussion(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        poster = self.login()
        response = self.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'new bla bla'
        })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 1)

        data = response.json

        self.assertEqual(data['subject'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertIsNone(data['closed'])
        self.assertIsNone(data['closed_by'])
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'new bla bla')
        self.assertEqual(
            data['discussion'][1]['posted_by']['id'], str(poster.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_discussion(self):
        owner = self.login()
        user = UserFactory()
        dataset = Dataset.objects.create(title='Test dataset', owner=owner)
        message = Message(content='bla bla', posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        response = self.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'close bla bla',
            'close': True
        })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 0)

        data = response.json

        self.assertEqual(data['subject'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertIsNotNone(data['closed'])
        self.assertEqual(data['closed_by'], str(owner.id))
        self.assertEqual(len(data['discussion']), 2)
        self.assertEqual(data['discussion'][1]['content'], 'close bla bla')
        self.assertEqual(
            data['discussion'][1]['posted_by']['id'], str(owner.id))
        self.assertIsNotNone(data['discussion'][1]['posted_on'])

    def test_close_discussion_permissions(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        self.login()
        response = self.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'close bla bla',
            'close': True
        })
        self.assert403(response)

        dataset.reload()
        # Metrics unchanged after attempt to close the discussion.
        self.assertEqual(dataset.metrics['discussions'], 1)

    def test_delete_discussion(self):
        owner = self.login(AdminFactory())
        user = UserFactory()
        dataset = Dataset.objects.create(title='Test dataset', owner=owner)
        message = Message(content='bla bla', posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.
        self.assertEqual(DatasetDiscussion.objects(subject=dataset.id).count(),
                         1)

        response = self.delete(url_for('api.discussion', id=discussion.id))
        self.assertStatus(response, 204)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 0)
        self.assertEqual(DatasetDiscussion.objects(subject=dataset.id).count(),
                         0)

    def test_delete_discussion_permissions(self):
        owner = self.login()
        dataset = Dataset.objects.create(title='Test dataset', owner=owner)
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset.id,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        self.login()
        response = self.delete(url_for('api.discussion', id=discussion.id))
        self.assert403(response)

        dataset.reload()
        # Metrics unchanged after attempt to delete the discussion.
        self.assertEqual(dataset.metrics['discussions'], 1)


class DiscussionCsvTest(FrontTestCase):

    def test_discussions_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(
            url_for('organizations.discussions_csv', org=organization))
        self.assert200(response)

        self.assertEqual(
            response.data,
            ('"id";"user";"subject";"title";"size";"messages";"created";'
             '"closed";"closed_by"\r\n')
        )

    def test_discussions_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name='John', last_name='Snow')
        discussion = DatasetDiscussionFactory(subject=dataset, user=user)
        response = self.get(
            url_for('organizations.discussions_csv', org=organization))
        self.assert200(response)

        headers, data = response.data.strip().split('\r\n')
        self.assertStartswith(
            data,
            '"{discussion.id}";"{discussion.user}"'.format(
                discussion=discussion))


class DiscussionsNotificationsTest(TestCase, DBTestMixin):
    def test_notify_user_discussions(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        open_discussions = {}
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = DatasetDiscussion.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_discussions[discussion.id] = discussion
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        notifications = discussions_notifications(owner)

        self.assertEqual(len(notifications), len(open_discussions))

        for dt, details in notifications:
            discussion = open_discussions[details['id']]
            self.assertEqual(details['title'], discussion.title)
            self.assertEqual(details['subject']['id'], discussion.subject.id)
            self.assertEqual(details['subject']['type'], 'dataset')

    def test_notify_org_discussions(self):
        recipient = UserFactory()
        member = Member(user=recipient, role='editor')
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(organization=org)

        open_discussions = {}
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = DatasetDiscussion.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_discussions[discussion.id] = discussion
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = DatasetDiscussion.objects.create(
            subject=dataset,
            user=user,
            title=faker.sentence(),
            discussion=[message],
            closed=datetime.now(),
            closed_by=user
        )

        notifications = discussions_notifications(recipient)

        self.assertEqual(len(notifications), len(open_discussions))

        for dt, details in notifications:
            discussion = open_discussions[details['id']]
            self.assertEqual(details['title'], discussion.title)
            self.assertEqual(details['subject']['id'], discussion.subject.id)
            self.assertEqual(details['subject']['type'], 'dataset')
