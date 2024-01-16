from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.topic.models import Topic
from udata.core.topic.factories import TopicFactory
from udata.core.user.factories import UserFactory
from udata.models import Member, Discussion

from . import APITestCase


class TopicsAPITest(APITestCase):
    modules = []

    def test_topic_api_list(self):
        '''It should fetch a topic list from the API'''
        TopicFactory.create_batch(3)
        tag_topic = TopicFactory(tags=['energy'])
        name_topic = TopicFactory(name='topic-for-query')

        response = self.get(url_for('api.topics'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 5)

        response = self.get(url_for('api.topics', q='topic-for'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(name_topic.id))

        response = self.get(url_for('api.topics', tag='energy'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['id'], str(tag_topic.id))
        datasets = response.json['data'][0]['datasets']
        self.assertEqual(len(datasets), 3)
        for dataset, expected in zip(datasets, [d.fetch() for d in tag_topic.datasets]):
            self.assertEqual(dataset['id'], str(expected.id))
            self.assertEqual(dataset['title'], str(expected.title))
            self.assertIsNotNone(dataset['page'])
            self.assertIsNotNone(dataset['uri'])
        reuses = response.json['data'][0]['reuses']
        for reuse, expected in zip(reuses, [r.fetch() for r in tag_topic.reuses]):
            self.assertEqual(reuse['id'], str(expected.id))
            self.assertEqual(reuse['title'], str(expected.title))
            self.assertIsNotNone(reuse['page'])
            self.assertIsNotNone(reuse['uri'])
        self.assertEqual(len(reuses), 3)

    def test_topic_api_get(self):
        '''It should fetch a topic from the API'''
        topic = TopicFactory()
        response = self.get(url_for('api.topic', topic=topic))
        self.assert200(response)

        data = response.json
        for dataset, expected in zip(data['datasets'], [d.fetch() for d in topic.datasets]):
            self.assertEqual(dataset['id'], str(expected.id))
            self.assertEqual(dataset['title'], str(expected.title))
            self.assertIsNotNone(dataset['page'])
            self.assertIsNotNone(dataset['uri'])

        for reuse, expected in zip(data['reuses'], [r.fetch() for r in topic.reuses]):
            self.assertEqual(reuse['id'], str(expected.id))
            self.assertEqual(reuse['title'], str(expected.title))
            self.assertIsNotNone(reuse['page'])
            self.assertIsNotNone(reuse['uri'])

    def test_topic_api_create(self):
        '''It should create a topic from the API'''
        data = TopicFactory.as_dict()
        data['datasets'] = [str(d.id) for d in data['datasets']]
        data['reuses'] = [str(r.id) for r in data['reuses']]
        self.login()
        response = self.post(url_for('api.topics'), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        for dataset, expected in zip(topic.datasets, data['datasets']):
            self.assertEqual(str(dataset.id), expected)
        for reuse, expected in zip(topic.reuses, data['reuses']):
            self.assertEqual(str(reuse.id), expected)

    def test_topic_api_create_as_org(self):
        '''It should create a topic as organization from the API'''
        data = TopicFactory.as_dict()
        data['datasets'] = [str(d.id) for d in data['datasets']]
        data['reuses'] = [str(r.id) for r in data['reuses']]
        user = self.login()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)
        response = self.post(url_for('api.topics'), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)

        topic = Topic.objects.first()
        assert topic.owner is None
        assert topic.organization == org

    def test_topic_api_update(self):
        '''It should update a topic from the API'''
        owner = self.login()
        topic = TopicFactory(owner=owner)
        data = topic.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.topic', topic=topic), data)
        self.assert200(response)
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Topic.objects.first().description, 'new description')

    def test_topic_api_update_perm(self):
        '''It should not update a topic from the API'''
        owner = UserFactory()
        topic = TopicFactory(owner=owner)
        user = self.login()
        data = topic.to_dict()
        data['owner'] = user.to_dict()
        response = self.put(url_for('api.topic', topic=topic), data)
        self.assert403(response)

    def test_topic_api_delete(self):
        '''It should delete a topic from the API'''
        owner = self.login()
        topic = TopicFactory(owner=owner)

        with self.api_user():
            response = self.post(url_for('api.discussions'), {
                'title': 'test title',
                'comment': 'bla bla',
                'subject': {
                    'class': 'Topic',
                    'id': topic.id,
                }
            })
        self.assert201(response)

        discussions = Discussion.objects(subject=topic)
        self.assertEqual(len(discussions), 1)

        with self.api_user():
            response = self.delete(url_for('api.topic', topic=topic))
        self.assertStatus(response, 204)

        self.assertEqual(Topic.objects.count(), 0)
        self.assertEqual(Discussion.objects.count(), 0)

    def test_topic_api_delete_perm(self):
        '''It should not delete a topic from the API'''
        owner = UserFactory()
        topic = TopicFactory(owner=owner)
        with self.api_user():
            response = self.delete(url_for('api.topic', topic=topic))
        self.assertStatus(response, 403)
