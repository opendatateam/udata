from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.topic.factories import TopicFactory
from udata.models import Member
from udata.tests.api import APITestCase


class MeAPIv2Test(APITestCase):
    modules = []

    def test_my_org_topics(self):
        user = self.login()
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(members=[member])
        topics = [
            TopicFactory(organization=organization, private=False, tags=["energy"]),
            TopicFactory(organization=organization, private=True),
            TopicFactory(owner=user),
        ]
        # another topic that shouldn't pop up
        TopicFactory()

        response = self.get(url_for("apiv2.my_org_topics"))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 3
        assert all(
            str(topic.id) in [remote_topic["id"] for remote_topic in data] for topic in topics
        )
        assert "rel" in data[0]["datasets"]

        # topic parser is already tested in topics test
        # we're just making sure one of theme is working
        response = self.get(url_for("apiv2.my_org_topics", tag="energy"))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(topics[0].id)
