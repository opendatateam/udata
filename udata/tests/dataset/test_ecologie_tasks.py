import pytest

from udata.core.dataset.ecologie import map_ecologie_datasets
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.topic.factories import TopicElementFactory, TopicFactory
from udata.tests.api import PytestOnlyDBTestCase

TOPIC_ID = "6adb0d4e615c7cccb709fbd6"


class EcologieTasksTest(PytestOnlyDBTestCase):
    @pytest.mark.options(ECOLOGIE_TOPIC_ID=TOPIC_ID)
    def test_map_ecologie_datasets(self):
        topic = TopicFactory(id=TOPIC_ID)
        other_topic = TopicFactory()
        in_topic = DatasetFactory()
        already_flagged = DatasetFactory(extras={"ecologie:universe": True})
        left_topic = DatasetFactory(extras={"ecologie:universe": True, "other": "kept"})
        in_other_topic = DatasetFactory()
        TopicElementFactory(topic=topic, element=in_topic)
        TopicElementFactory(topic=topic, element=already_flagged)
        TopicElementFactory(topic=topic, element=ReuseFactory())
        TopicElementFactory(topic=other_topic, element=in_other_topic)

        map_ecologie_datasets()

        for dataset in (in_topic, already_flagged, left_topic, in_other_topic):
            dataset.reload()
        assert in_topic.extras["ecologie:universe"] is True
        assert already_flagged.extras["ecologie:universe"] is True
        assert "ecologie:universe" not in left_topic.extras
        assert left_topic.extras["other"] == "kept"
        assert "ecologie:universe" not in in_other_topic.extras

    @pytest.mark.options(ECOLOGIE_TOPIC_ID=TOPIC_ID)
    def test_map_ecologie_datasets_unknown_topic(self):
        """A deleted or misconfigured topic unflags everything"""
        flagged = DatasetFactory(extras={"ecologie:universe": True, "other": "kept"})

        map_ecologie_datasets()

        flagged.reload()
        assert "ecologie:universe" not in flagged.extras
        assert flagged.extras["other"] == "kept"

    def test_map_ecologie_datasets_no_config(self):
        """Unsetting the topic disables the feature"""
        flagged = DatasetFactory(extras={"ecologie:universe": True})

        map_ecologie_datasets()

        flagged.reload()
        assert "ecologie:universe" not in flagged.extras
