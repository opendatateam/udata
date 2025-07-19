import pytest

from udata.core.dataset.tasks import purge_datasets
from udata.core.reuse.tasks import purge_reuses
from udata.core.topic.factories import TopicFactory
from udata.core.topic.tasks import purge_topics_elements

pytestmark = pytest.mark.usefixtures("clean_db")


def test_purge_topics_elements():
    topic = TopicFactory()
    assert len(topic.elements) > 0
    for _element in topic.elements:
        element = _element.fetch()
        element.title = None
        element.save()
        element.element.deleted = "2023-01-01"
        element.element.save()
    topic.save()
    # remove the dataset elements marked as deleted
    purge_datasets()
    # remove the reuse elements marked as deleted
    purge_reuses()
    # remove the topic elements that have neither title nor element
    purge_topics_elements()
    topic.reload()
    assert len(topic.elements) == 0
