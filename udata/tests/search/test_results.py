from udata.tests.api import APITestCase
from udata.search.result import SearchResult
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.dataset.search import DatasetSearch
from udata.models import Dataset


class ResultTest(APITestCase):
    def test_results_get_objects(self):
        data = []
        for _ in range(3):
            random_dataset = VisibleDatasetFactory()
            data.append(DatasetSearch.serialize(random_dataset))

        search_class = DatasetSearch.temp_search()
        search_query = search_class(params={})
        service_result = {
            "data": data,
            "next_page": None,
            "page": 1,
            "previous_page": None,
            "page_size": 20,
            "total_pages": 1,
            "total": 3
        }
        search_results = SearchResult(query=search_query, result=service_result.pop('data'), **service_result)

        assert len(search_results.get_objects()) == 3

    def test_results_should_not_fail_on_missing_objects(self):
        data = []
        for _ in range(3):
            random_dataset = VisibleDatasetFactory()
            data.append(DatasetSearch.serialize(random_dataset))

        to_delete_random_dataset = VisibleDatasetFactory()
        data.append(DatasetSearch.serialize(to_delete_random_dataset))

        search_class = DatasetSearch.temp_search()
        search_query = search_class(params={})
        service_result = {
            "data": data,
            "next_page": None,
            "page": 1,
            "previous_page": None,
            "page_size": 20,
            "total_pages": 1,
            "total": 3
        }
        search_results = SearchResult(query=search_query, result=service_result.pop('data'), **service_result)

        to_delete_random_dataset.delete()
        assert len(search_results.get_objects()) == 3

        # Missing object should be filtered out
        objects = search_results.objects
        for o in objects:
            assert isinstance(o, Dataset)

