# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.models import Dataset, Member
from udata.core.user.views import blueprint as user_bp
from udata.core.dataset.views import blueprint as dataset_bp
from udata.core.discussions.models import Message, Discussion
from udata.core.discussions.notifications import discussions_notifications
from udata.core.discussions.signals import (
    on_new_discussion, on_new_discussion_comment,
    on_discussion_closed, on_discussion_deleted,
)
from udata.core.discussions.tasks import (
    notify_new_discussion, notify_new_discussion_comment,
    notify_discussion_closed
)
from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory, AdminFactory
from udata.utils import faker

from frontend import FrontTestCase

from . import TestCase, DBTestMixin
from .api import APITestCase


class DiscussionsTest(APITestCase):
    def create_app(self):
        app = super(DiscussionsTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_discussion(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        with self.assert_emit(on_new_discussion):
            response = self.post(url_for('api.discussions'), {
                'title': 'test title',
                'comment': 'bla bla',
                'subject': {
                    'class': 'Dataset',
                    'id': dataset.id,
                }
            })
        self.assert201(response)

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
            'subject': {
                'class': 'Dataset',
                'id': dataset.id,
            }
        })
        self.assertStatus(response, 400)

    def test_new_discussion_missing_title(self):
        self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        response = self.post(url_for('api.discussions'), {
            'comment': 'bla bla',
            'subject': {
                'class': 'Dataset',
                'id': dataset.id,
            }
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
        closed_discussions = []
        for i in range(2):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            open_discussions.append(discussion)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_discussions.append(discussion)

        response = self.get(url_for('api.discussions'))
        self.assert200(response)

        self.assertEqual(len(response.json['data']),
                         len(open_discussions + closed_discussions))

    def test_list_discussions_closed_filter(self):
        dataset = Dataset.objects.create(title='Test dataset')
        open_discussions = []
        closed_discussions = []
        for i in range(2):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            open_discussions.append(discussion)
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message],
                closed=datetime.now(),
                closed_by=user
            )
            closed_discussions.append(discussion)

        response = self.get(url_for('api.discussions', closed=True))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(closed_discussions))
        for discussion in response.json['data']:
            self.assertIsNotNone(discussion['closed'])

    def test_list_discussions_for(self):
        dataset = DatasetFactory()
        discussions = []
        for i in range(3):
            user = UserFactory()
            message = Message(content=faker.sentence(), posted_by=user)
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title='test discussion {}'.format(i),
                discussion=[message]
            )
            discussions.append(discussion)
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        Discussion.objects.create(
            subject=DatasetFactory(),
            user=user,
            title='test discussion {}'.format(i),
            discussion=[message]
        )

        kwargs = {'for': str(dataset.id)}
        response = self.get(url_for('api.discussions', **kwargs))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), len(discussions))

    def test_get_discussion(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        response = self.get(url_for('api.discussion', **{'id': discussion.id}))
        self.assert200(response)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
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
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        poster = self.login()
        with self.assert_emit(on_new_discussion_comment):
            response = self.post(url_for('api.discussion', id=discussion.id), {
                'comment': 'new bla bla'
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 1)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
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
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.

        with self.assert_emit(on_discussion_closed):
            response = self.post(url_for('api.discussion', id=discussion.id), {
                'comment': 'close bla bla',
                'close': True
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 0)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
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
        discussion = Discussion.objects.create(
            subject=dataset,
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
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        on_new_discussion.send(discussion)  # Updating metrics.
        self.assertEqual(Discussion.objects(subject=dataset).count(), 1)

        with self.assert_emit(on_discussion_deleted):
            response = self.delete(url_for('api.discussion', id=discussion.id))
        self.assertStatus(response, 204)

        dataset.reload()
        self.assertEqual(dataset.metrics['discussions'], 0)
        self.assertEqual(Discussion.objects(subject=dataset).count(), 0)

    def test_delete_discussion_permissions(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
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
        discussion = DiscussionFactory(subject=dataset, user=user)
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
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_discussions[discussion.id] = discussion
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
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
            discussion = Discussion.objects.create(
                subject=dataset,
                user=user,
                title=faker.sentence(),
                discussion=[message]
            )
            open_discussions[discussion.id] = discussion
        # Creating a closed discussion that shouldn't show up in response.
        user = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
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


class DiscussionsMailsTest(TestCase, DBTestMixin):
    def create_app(self):
        app = super(DiscussionsMailsTest, self).create_app()
        app.register_blueprint(user_bp)
        app.register_blueprint(dataset_bp)
        return app

    def test_new_discussion_mail(self):
        user = UserFactory()
        owner = UserFactory()
        message = Message(content=faker.sentence(), posted_by=user)
        discussion = Discussion.objects.create(
            subject=DatasetFactory(owner=owner),
            user=user,
            title=faker.sentence(),
            discussion=[message]
        )

        with self.capture_mails() as mails:
            notify_new_discussion(discussion)

        # Should have sent one mail to the owner
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].recipients[0], owner.email)

    def test_new_discussion_comment_mail(self):
        owner = UserFactory()
        poster = UserFactory()
        commenter = UserFactory()
        message = Message(content=faker.sentence(), posted_by=poster)
        new_message = Message(content=faker.sentence(), posted_by=commenter)
        discussion = Discussion.objects.create(
            subject=DatasetFactory(owner=owner),
            user=poster,
            title=faker.sentence(),
            discussion=[message, new_message]
        )

        with self.capture_mails() as mails:
            notify_new_discussion_comment(discussion, message=new_message)

        # Should have sent one mail to the owner and the other participants
        # and no mail to the commenter
        expected_recipients = (owner.email, poster.email)
        self.assertEqual(len(mails), len(expected_recipients))
        for mail in mails:
            self.assertIn(mail.recipients[0], expected_recipients)
            self.assertNotIn(commenter.email, mail.recipients)

    def test_closed_discussion_mail(self):
        owner = UserFactory()
        poster = UserFactory()
        commenter = UserFactory()
        message = Message(content=faker.sentence(), posted_by=poster)
        second_message = Message(content=faker.sentence(), posted_by=commenter)
        closing_message = Message(content=faker.sentence(), posted_by=owner)
        discussion = Discussion.objects.create(
            subject=DatasetFactory(owner=owner),
            user=poster,
            title=faker.sentence(),
            discussion=[message, second_message, closing_message]
        )

        with self.capture_mails() as mails:
            notify_discussion_closed(discussion, message=closing_message)

        # Should have sent one mail to each participant
        # and no mail to the closer
        expected_recipients = (poster.email, commenter.email)
        self.assertEqual(len(mails), len(expected_recipients))
        for mail in mails:
            self.assertIn(mail.recipients[0], expected_recipients)
            self.assertNotIn(owner.email, mail.recipients)
