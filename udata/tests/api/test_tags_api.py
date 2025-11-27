from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.tags.tasks import count_tags
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200
from udata.utils import faker


class TagsAPITest(PytestOnlyAPITestCase):
    def test_suggest_tags_api(self):
        """It should suggest tags"""
        for i in range(3):
            tags = [faker.tag(), faker.tag(), "test", "test-{0}".format(i)]
            ReuseFactory(tags=tags, visible=True)
            DatasetFactory(tags=tags, visible=True)

        count_tags()

        response = self.get(url_for("api.suggest_tags", q="tes", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1
        assert response.json[0]["text"] == "test"

        for suggestion in response.json:
            assert "text" in suggestion
            assert "tes" in suggestion["text"]

    def test_suggest_tags_api_with_unicode(self):
        """It should suggest tags"""
        for i in range(3):
            tags = [faker.tag(), faker.tag(), "testé", "testé-{0}".format(i)]
            ReuseFactory(tags=tags, visible=True)
            DatasetFactory(tags=tags, visible=True)

        count_tags()

        response = self.get(url_for("api.suggest_tags", q="testé", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1
        assert response.json[0]["text"] == "teste"

        for suggestion in response.json:
            assert "text" in suggestion
            assert "teste" in suggestion["text"]

    def test_suggest_tags_api_no_match(self):
        """It should not provide tag suggestion if no match"""
        for i in range(3):
            tags = ["aaaa", "aaaa-{0}".format(i)]
            ReuseFactory(tags=tags, visible=True)
            DatasetFactory(tags=tags, visible=True)

        count_tags()

        response = self.get(url_for("api.suggest_tags", q="bbbb", size=5))
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_tags_api_empty(self):
        """It should not provide tag suggestion if no data"""
        response = self.get(url_for("api.suggest_tags", q="bbbb", size=5))
        assert200(response)
        assert len(response.json) == 0
