from flask import url_for

from udata.core.topic.models import Topic
from udata.core.topic.factories import TopicFactory
from udata.core.organization.factories import OrganizationFactory
from udata.models import Member

from . import APITestCase


class TopicsAPITest(APITestCase):
    modules = []

    def test_topic_api_list(self):
        '''It should fetch a topic list from the API'''
        topics = TopicFactory.create_batch(3)

        response = self.get(url_for('api.topics'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(topics))

    def test_topic_api_get(self):
        '''It should fetch a topic from the API'''
        topic = TopicFactory()
        response = self.get(url_for('api.topic', topic=topic))
        self.assert200(response)

        data = response.json
        for dataset, expected in zip(data['datasets'], topic.datasets):
            self.assertEqual(dataset['id'], str(expected.id))

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
        topic = TopicFactory()
        data = topic.to_dict()
        data['description'] = 'new description'
        self.login()
        response = self.put(url_for('api.topic', topic=topic), data)
        self.assert200(response)
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Topic.objects.first().description, 'new description')

    def test_topic_api_delete(self):
        '''It should delete a topic from the API'''
        topic = TopicFactory()
        with self.api_user():
            response = self.delete(url_for('api.topic', topic=topic))
        self.assertStatus(response, 204)
        self.assertEqual(Topic.objects.count(), 0)
