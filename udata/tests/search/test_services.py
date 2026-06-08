from unittest.mock import MagicMock

from udata_search_service.services import DatasetService


def make_service():
    mock_client = MagicMock()
    mock_client.query_datasets.return_value = (0, [], {})
    return DatasetService(mock_client), mock_client


def base_filters():
    return {"q": "", "page": 1, "page_size": 20, "sort": None}


def test_facet_sizes_passed_to_client_query():
    service, mock_client = make_service()
    filters = {**base_filters(), "facet_sizes": {"organization_id_with_name": 200}}
    service.search(filters)
    _, kwargs = mock_client.query_datasets.call_args
    assert kwargs["facet_sizes"] == {"organization_id_with_name": 200}


def test_empty_facet_sizes_when_not_provided():
    service, mock_client = make_service()
    service.search(base_filters())
    _, kwargs = mock_client.query_datasets.call_args
    assert kwargs["facet_sizes"] == {}


def test_facet_sizes_not_passed_as_filter():
    service, mock_client = make_service()
    filters = {**base_filters(), "facet_sizes": {"tag": 100}}
    service.search(filters)
    args, _ = mock_client.query_datasets.call_args
    # 4th positional arg is the filters dict
    filters_arg = args[3]
    assert "facet_sizes" not in filters_arg
