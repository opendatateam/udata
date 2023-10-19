from flask import url_for

from udata.tests.api import APITestCase
from udata.core.topic.factories import TopicFactory


class TopicsAPITest(APITestCase):
    modules = []

    def test_topic_api_list(self):
        '''It should fetch a topic list from the API'''
        TopicFactory.create_batch(3)
        tag_topic = TopicFactory(tags=['energy'])
        name_topic = TopicFactory(name='topic-for-query')

        response = self.get(url_for('apiv2.topics_list'))
        assert response.status_code == 200
        data = response.json['data']
        assert len(data) == 5

        assert all(k in data[0]["datasets"] for k in ["rel", "href", "type", "total"])
        assert all(k in data[0]["reuses"] for k in ["rel", "href", "type", "total"])

        response = self.get(url_for('apiv2.topics_list', q='topic-for'))
        assert response.status_code == 200
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == str(name_topic.id)

        response = self.get(url_for('apiv2.topics_list', tag='energy'))
        assert response.status_code == 200
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == str(tag_topic.id)

    def test_topic_api_get(self):
        '''It should fetch a topic from the API'''
        topic = TopicFactory()
        topic_response = self.get(url_for('apiv2.topic', topic=topic))
        assert topic_response.status_code == 200

        response = self.get(topic_response.json['datasets']['href'])
        data = response.json
        assert all(str(d.id) in (_d['id'] for _d in data['data']) for d in topic.datasets)

        response = self.get(topic_response.json['reuses']['href'])
        data = response.json
        assert all(str(r.id) in (_r['id'] for _r in data['data']) for r in topic.reuses)


class TopicDatasetsAPITest(APITestCase):
    def test_topic_datasets_list(self):
        topic = TopicFactory()
        response = self.get(url_for('apiv2.topic_datasets', topic=topic))
        assert response.status_code == 200
        data = response.json['data']
        assert len(data) == 3
        assert all(str(d.id) in (_d['id'] for _d in data) for d in topic.datasets)


class TopicReusesAPITest(APITestCase):
    def test_topic_datasets_list(self):
        topic = TopicFactory()
        response = self.get(url_for('apiv2.topic_reuses', topic=topic))
        assert response.status_code == 200
        data = response.json['data']
        assert len(data) == 3
        assert all(str(r.id) in (_r['id'] for _r in data) for r in topic.reuses)
