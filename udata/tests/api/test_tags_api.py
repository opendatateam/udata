import pytest

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.utils import faker
from udata.tests.helpers import assert200


@pytest.mark.frontend
class TagsAPITest:
    def test_suggest_tags_api(self, api, autoindex):
        '''It should suggest tags'''
        with autoindex:
            for i in range(3):
                tags = [faker.word(), faker.word(), 'test',
                        'test-{0}'.format(i)]
                ReuseFactory(tags=tags, visible=True)
                DatasetFactory(tags=tags, visible=True)

        response = api.get(url_for('api.suggest_tags'),
                            qs={'q': 'tes', 'size': '5'})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1
        assert response.json[0]['text'] == 'test'

        for suggestion in response.json:
            assert 'text' in suggestion
            assert 'score' in suggestion
            assert suggestion['text'].startswith('test')

    def test_suggest_tags_api_with_unicode(self, api, autoindex):
        '''It should suggest tags'''
        with autoindex:
            for i in range(3):
                tags = [faker.word(), faker.word(), 'testé',
                        'testé-{0}'.format(i)]
                ReuseFactory(tags=tags, visible=True)
                DatasetFactory(tags=tags, visible=True)

        response = api.get(url_for('api.suggest_tags'),
                           qs={'q': 'testé', 'size': '5'})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1
        assert response.json[0]['text'] == 'teste'

        for suggestion in response.json:
            assert 'text' in suggestion
            assert 'score' in suggestion
            assert suggestion['text'].startswith('teste')

    def test_suggest_tags_api_no_match(self, api, autoindex):
        '''It should not provide tag suggestion if no match'''
        with autoindex:
            for i in range(3):
                tags = ['aaaa', 'aaaa-{0}'.format(i)]
                ReuseFactory(tags=tags, visible=True)
                DatasetFactory(tags=tags, visible=True)

        response = api.get(url_for('api.suggest_tags'),
                           qs={'q': 'bbbb', 'size': '5'})
        assert200(response)
        assert len(response.json) is 0

    def test_suggest_tags_api_empty(self, api, autoindex):
        '''It should not provide tag suggestion if no data'''
        response = api.get(url_for('api.suggest_tags'),
                           qs={'q': 'bbbb', 'size': '5'})
        assert200(response)
        assert len(response.json) is 0
