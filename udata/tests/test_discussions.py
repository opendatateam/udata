from datetime import datetime

from flask import url_for

from udata.models import Dataset, Member
from udata.core.discussions.models import Message, Discussion
from udata.core.discussions.metrics import update_discussions_metric
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
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory, AdminFactory
from udata.utils import faker

from . import TestCase, DBTestMixin
from .api import APITestCase
from .helpers import assert_emit


class DiscussionsTest(APITestCase):
    modules = []

    def test_new_discussion(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset')

        with assert_emit(on_new_discussion):
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
        self.assertEqual(dataset.get_metrics()['discussions'], 1)

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

    def test_new_discussion_with_extras(self):
        user = self.login()
        dataset = Dataset.objects.create(title='Test dataset',
                                         extras={'key': 'value'})

        with assert_emit(on_new_discussion):
            response = self.post(url_for('api.discussions'), {
                'title': 'test title',
                'comment': 'bla bla',
                'subject': {
                    'class': 'Dataset',
                    'id': dataset.id,
                },
                'extras': {'key': 'value'}
            })
        self.assert201(response)

        discussions = Discussion.objects(subject=dataset)
        self.assertEqual(len(discussions), 1)

        discussion = discussions[0]
        self.assertEqual(discussion.user, user)
        self.assertEqual(len(discussion.discussion), 1)
        self.assertEqual(discussion.title, 'test title')
        self.assertEqual(discussion.extras, {u'key': u'value'})

        message = discussion.discussion[0]
        self.assertEqual(message.content, 'bla bla')
        self.assertEqual(message.posted_by, user)
        self.assertIsNotNone(message.posted_on)

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
                closed=datetime.utcnow(),
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
                closed=datetime.utcnow(),
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

    def test_list_discussions_user(self):
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
            title='test discussion {}'.format(i+1),
            discussion=[message]
        )

        kwargs = {'user': str(user.id)}
        response = self.get(url_for('api.discussions', **kwargs))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['user']['id'], str(user.id))

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
        with assert_emit(on_new_discussion_comment):
            response = self.post(url_for('api.discussion', id=discussion.id), {
                'comment': 'new bla bla'
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()['discussions'], 1)

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

        with assert_emit(on_discussion_closed):
            response = self.post(url_for('api.discussion', id=discussion.id), {
                'comment': 'close bla bla',
                'close': True
            })
        self.assert200(response)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()['discussions'], 0)

        data = response.json

        self.assertEqual(data['subject']['class'], 'Dataset')
        self.assertEqual(data['subject']['id'], str(dataset.id))
        self.assertEqual(data['user']['id'], str(user.id))
        self.assertEqual(data['title'], 'test discussion')
        self.assertIsNotNone(data['created'])
        self.assertIsNotNone(data['closed'])
        self.assertEqual(data['closed_by']['id'], str(owner.id))
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
        self.assertEqual(dataset.get_metrics()['discussions'], 1)

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

        with assert_emit(on_discussion_deleted):
            response = self.delete(url_for('api.discussion', id=discussion.id))
        self.assertStatus(response, 204)

        dataset.reload()
        self.assertEqual(dataset.get_metrics()['discussions'], 0)
        self.assertEqual(Discussion.objects(subject=dataset).count(), 0)

    def test_delete_discussion_comment(self):
        owner = self.login(AdminFactory())
        user = UserFactory()
        dataset = Dataset.objects.create(title='Test dataset', owner=owner)
        message = Message(content='bla bla', posted_by=user)
        message2 = Message(content='bla bla bla', posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message, message2]
        )
        self.assertEqual(len(discussion.discussion), 2)

        # test first comment deletion
        response = self.delete(url_for('api.discussion_comment',
                               id=discussion.id, cidx=0))
        self.assertStatus(response, 400)

        # test effective deletion
        response = self.delete(url_for('api.discussion_comment',
                               id=discussion.id, cidx=1))
        self.assertStatus(response, 204)
        discussion.reload()
        self.assertEqual(len(discussion.discussion), 1)
        self.assertEqual(discussion.discussion[0].content, 'bla bla')

        # delete again to test list overflow
        response = self.delete(url_for('api.discussion_comment',
                               id=discussion.id, cidx=3))
        self.assertStatus(response, 404)

        # delete again to test last comment deletion
        response = self.delete(url_for('api.discussion_comment',
                               id=discussion.id, cidx=0))
        self.assertStatus(response, 400)

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
        self.assertEqual(dataset.get_metrics()['discussions'], 1)

    def test_delete_discussion_comment_permissions(self):
        dataset = Dataset.objects.create(title='Test dataset')
        user = UserFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        self.login()
        response = self.delete(url_for('api.discussion_comment',
                               id=discussion.id, cidx=0))
        self.assert403(response)


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
            closed=datetime.utcnow(),
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
            closed=datetime.utcnow(),
            closed_by=user
        )

        notifications = discussions_notifications(recipient)

        self.assertEqual(len(notifications), len(open_discussions))

        for dt, details in notifications:
            discussion = open_discussions[details['id']]
            self.assertEqual(details['title'], discussion.title)
            self.assertEqual(details['subject']['id'], discussion.subject.id)
            self.assertEqual(details['subject']['type'], 'dataset')
