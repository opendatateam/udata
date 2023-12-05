import pytest

from udata.search import reindex
from udata.core.topic.factories import TopicFactory
from udata.core.dataset.factories import DatasetFactory


@pytest.fixture
def job_reindex(mocker):
    return mocker.patch.object(reindex, 'delay')


@pytest.fixture
def job_reindex_undelayed(mocker):
    """Mock the reindex.delay fn to access the underlying reindex fn"""
    return mocker.patch.object(reindex, 'delay', side_effect=reindex)


pytestmark = pytest.mark.usefixtures('clean_db')

class TopicModelTest:
    # allows url_for with correct context when calling reindex
    modules = ["admin"]

    def test_pre_save(self, job_reindex):
        topic = TopicFactory(datasets=[])
        dataset = DatasetFactory()

        topic.name = 'new_name'
        topic.save()
        job_reindex.assert_not_called()

        topic.datasets = [dataset]
        topic.save()
        job_reindex.assert_called()

        topic.datasets = []
        topic.save()
        job_reindex.assert_called()

    @pytest.mark.options(SEARCH_SERVICE_API_URL="smtg")
    def test_pre_save_reindex(self, job_reindex_undelayed):
        """This will call the real reindex method and thus bubble up errors"""
        # creates a topic with datasets, thus calls reindex
        TopicFactory()
        job_reindex_undelayed.assert_called()

