import pytest
from mongoengine.errors import ValidationError

from udata.core.discussions.factories import DiscussionFactory
from udata.core.topic.activities import UserCreatedTopic, UserUpdatedTopic
from udata.core.topic.factories import (
    TopicElementDatasetFactory,
    TopicElementFactory,
    TopicFactory,
    TopicWithElementsFactory,
)
from udata.core.topic.models import Topic
from udata.search import reindex
from udata.tests.helpers import assert_emit


@pytest.fixture
def job_reindex(mocker):
    return mocker.patch.object(reindex, "delay")


@pytest.fixture
def job_reindex_undelayed(mocker):
    """Mock the reindex.delay fn to access the underlying reindex fn"""
    return mocker.patch.object(reindex, "delay", side_effect=reindex)


pytestmark = pytest.mark.usefixtures("clean_db")


class TopicModelTest:
    # allows url_for with correct context when calling reindex
    modules = ["admin"]

    def test_pre_save(self, job_reindex):
        topic = TopicFactory()

        topic.name = "new_name"
        topic.save()
        job_reindex.assert_not_called()

        TopicElementDatasetFactory(topic=topic)
        topic.save()
        job_reindex.assert_called()

        topic.elements.delete()
        topic.save()
        job_reindex.assert_called()

    @pytest.mark.options(SEARCH_SERVICE_API_URL="smtg")
    def test_pre_save_reindex(self, job_reindex_undelayed):
        """This will call the real reindex method and thus bubble up errors"""
        # creates a topic with elements, thus calls reindex
        TopicWithElementsFactory()
        job_reindex_undelayed.assert_called()

    def test_topic_activities(self, api, mocker):
        # A user must be authenticated for activities to be emitted
        user = api.login()

        mock_created = mocker.patch.object(UserCreatedTopic, "emit")
        mock_updated = mocker.patch.object(UserUpdatedTopic, "emit")

        with assert_emit(Topic.on_create):
            topic = TopicFactory(owner=user)
            mock_created.assert_called()

        with assert_emit(Topic.on_update):
            topic.name = "new name"
            topic.save()
            mock_updated.assert_called()

    def test_topic_element_wrong_class(self):
        # use a model instance that is not supported
        with pytest.raises(ValidationError):
            topic = TopicFactory()
            TopicElementFactory(topic=topic, element=DiscussionFactory())
