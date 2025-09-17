import pytest
from mongoengine.errors import ValidationError

from udata.core.discussions.factories import DiscussionFactory
from udata.core.topic.activities import (
    UserCreatedTopic,
    UserCreatedTopicElement,
    UserDeletedTopicElement,
    UserUpdatedTopic,
    UserUpdatedTopicElement,
)
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

    def test_topic_element_activities(self, api, mocker):
        # A user must be authenticated for activities to be emitted
        user = api.login()
        topic = TopicFactory(owner=user)

        mock_topic_created = mocker.patch.object(UserCreatedTopic, "emit")
        mock_topic_updated = mocker.patch.object(UserUpdatedTopic, "emit")
        mock_element_created = mocker.patch.object(UserCreatedTopicElement, "emit")
        mock_element_updated = mocker.patch.object(UserUpdatedTopicElement, "emit")
        mock_element_deleted = mocker.patch.object(UserDeletedTopicElement, "emit")

        # Test TopicElement creation
        element = TopicElementDatasetFactory(topic=topic)
        mock_element_created.assert_called_once()
        mock_topic_created.assert_not_called()
        mock_topic_updated.assert_not_called()
        mock_element_updated.assert_not_called()
        mock_element_deleted.assert_not_called()

        call_args = mock_element_created.call_args
        assert call_args[0][0] == topic  # related_to
        assert call_args[0][1] == topic.organization  # organization
        assert call_args[1]["extras"]["element_id"] == str(element.id)

        mock_element_created.reset_mock()

        # Test TopicElement update
        element.title = "Updated title"
        element.extras = {"key": "value"}
        element.save()
        mock_element_updated.assert_called_once()
        mock_topic_created.assert_not_called()
        mock_topic_updated.assert_not_called()
        mock_element_created.assert_not_called()
        mock_element_deleted.assert_not_called()

        call_args = mock_element_updated.call_args
        assert call_args[0][0] == topic  # related_to
        assert call_args[0][1] == topic.organization  # organization
        assert call_args[0][2] == ["title", "extras"]  # changed_fields
        assert call_args[1]["extras"]["element_id"] == str(element.id)

        mock_element_updated.reset_mock()

        # Test TopicElement deletion
        element_id = element.id
        element.delete()

        # Deletion should only trigger delete activity
        mock_element_deleted.assert_called_once()
        mock_element_updated.assert_not_called()
        mock_topic_created.assert_not_called()
        mock_topic_updated.assert_not_called()
        mock_element_created.assert_not_called()

        # Verify delete activity arguments
        delete_call_args = mock_element_deleted.call_args
        assert delete_call_args[0][0] == topic  # related_to
        assert delete_call_args[0][1] == topic.organization  # organization
        assert delete_call_args[1]["extras"]["element_id"] == str(element_id)

    def test_topic_element_wrong_class(self):
        # use a model instance that is not supported
        with pytest.raises(ValidationError):
            topic = TopicFactory()
            TopicElementFactory(topic=topic, element=DiscussionFactory())
