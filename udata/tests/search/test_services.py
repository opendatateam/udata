from udata_search_service.services import DatasetService


class FakeElasticClient:
    """Records the last query_datasets call so we can assert on the plumbing."""

    def __init__(self):
        self.last_call = None

    def index_dataset(self, *args, **kwargs):
        pass

    def find_one_dataset(self, *args, **kwargs):
        pass

    def delete_one_dataset(self, *args, **kwargs):
        pass

    def query_datasets(self, search_text, offset, page_size, filters, sort=None, **kwargs):
        self.last_call = {"filters": filters, "kwargs": kwargs}
        return 0, [], {}


def base_filters(**extra):
    return {"q": "", "page": 1, "page_size": 20, "sort": None, **extra}


def test_count_organizations_forwarded_when_set():
    client = FakeElasticClient()
    DatasetService(client).search(base_filters(count_organizations=["org-id-1", "org-id-2"]))
    assert client.last_call["kwargs"]["count_organizations"] == ["org-id-1", "org-id-2"]
    # It must not leak into the filters sent to ES as a regular filter.
    assert "count_organizations" not in client.last_call["filters"]


def test_count_organizations_not_forwarded_when_absent():
    client = FakeElasticClient()
    DatasetService(client).search(base_filters())
    assert "count_organizations" not in client.last_call["kwargs"]
