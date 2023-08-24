import pytest

from udata.search import reindex
from udata.core.topic.factories import TopicFactory
from udata.core.dataset.factories import DatasetFactory


@pytest.fixture
def job_reindex(mocker):
    return mocker.patch.object(reindex, 'delay')


pytestmark = pytest.mark.usefixtures('clean_db')


class TopicModelTest:

    def test_pre_save(self, job_reindex):
        topic = TopicFactory()
        dataset = DatasetFactory()
        topic.datasets = [dataset]
        topic.save()
        job_reindex.assert_called()
