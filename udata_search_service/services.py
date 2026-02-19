from typing import Tuple, Optional, List
from udata_search_service.domain.entities import Dataset, Organization, Reuse, Dataservice, Topic, Discussion, Post
from udata_search_service.infrastructure.search_clients import ElasticClient


class OrganizationService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, organization: Organization, index: str = None) -> None:
        self.search_client.index_organization(organization, index)

    def search(self, filters: dict) -> Tuple[List[Organization], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_organizations(search_text, offset, page_size, filters, sort)
        results = [Organization.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, organization_id: str) -> Optional[Organization]:
        try:
            return Organization.load_from_dict(self.search_client.find_one_organization(organization_id))
        except TypeError:
            return None

    def delete_one(self, organization_id: str) -> Optional[str]:
        return self.search_client.delete_one_organization(organization_id)

    @staticmethod
    def format_filters(filters):
        if filters['badge']:
            filters['badges'] = filters.pop('badge')
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        return sort


class DatasetService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, dataset: Dataset, index: str = None) -> None:
        self.search_client.index_dataset(dataset, index)

    def search(self, filters: dict) -> Tuple[List[Dataset], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_datasets(search_text, offset, page_size, filters, sort)
        results = [Dataset.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, dataset_id: str) -> Optional[Dataset]:
        try:
            return Dataset.load_from_dict(self.search_client.find_one_dataset(dataset_id))
        except TypeError:
            return None

    def delete_one(self, dataset_id: str) -> Optional[str]:
        return self.search_client.delete_one_dataset(dataset_id)

    @staticmethod
    def format_filters(filters):
        '''
        Format search filters params to match the actual fields in ElasticSearch.
        For example udata search params uses singular ?tag=<mytag>, even though
        the field is plural since it's a list of tags.
        '''
        if filters.get('temporal_coverage'):
            parts = filters.pop('temporal_coverage')
            filters['temporal_coverage_start'] = parts[:10]
            filters['temporal_coverage_end'] = parts[11:]
        if filters.get('tag'):
            filters['tags'] = filters.pop('tag')
        if filters.get('badge'):
            filters['badges'] = filters.pop('badge')
        if filters.get('topic'):
            filters['topics'] = filters.pop('topic')
        if filters.get('geozone'):
            filters['geozones'] = filters.pop('geozone')
        if filters.get('schema_'):
            filters['schema'] = filters.pop('schema_')
        if filters.get('organization_badge'):
            filters['organization_badges'] = filters.pop('organization_badge')
        if filters.get('organization'):
            filters['organization_id_with_name'] = filters.pop('organization')
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort is not None and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        return sort


class ReuseService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, reuse: Reuse, index: str = None) -> None:
        self.search_client.index_reuse(reuse, index)

    def search(self, filters: dict) -> Tuple[List[Reuse], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_reuses(search_text, offset, page_size, filters, sort)
        results = [Reuse.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, reuse_id: str) -> Optional[Reuse]:
        try:
            return Reuse.load_from_dict(self.search_client.find_one_reuse(reuse_id))
        except TypeError:
            return None

    def delete_one(self, reuse_id: str) -> Optional[str]:
        return self.search_client.delete_one_reuse(reuse_id)

    @staticmethod
    def format_filters(filters):
        if filters.get('tag'):
            filters['tags'] = filters.pop('tag')
        if filters.get('badge'):
            filters['badges'] = filters.pop('badge')
        # topic_object stays as is (no pluralization needed)
        if filters.get('organization_badge'):
            filters['organization_badges'] = filters.pop('organization_badge')
        if filters.get('organization'):
            filters['organization_id_with_name'] = filters.pop('organization')
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort is not None and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        return sort


class DataserviceService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, dataservice: Dataservice, index: str = None) -> None:
        self.search_client.index_dataservice(dataservice, index)

    def search(self, filters: dict) -> Tuple[List[Dataservice], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_dataservices(search_text, offset, page_size, filters, sort)
        results = [Dataservice.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, dataservice_id: str) -> Optional[Dataservice]:
        try:
            return Dataservice.load_from_dict(self.search_client.find_one_dataservice(dataservice_id))
        except TypeError:
            return None

    def delete_one(self, dataservice_id: str) -> Optional[str]:
        return self.search_client.delete_one_dataservice(dataservice_id)

    @staticmethod
    def format_filters(filters):
        if filters.get('tag'):
            filters['tags'] = filters.pop('tag')
        if filters.get('badge'):
            filters['badges'] = filters.pop('badge')
        if filters.get('topic'):
            filters['topics'] = filters.pop('topic')
        if filters.get('organization'):
            filters['organization_id_with_name'] = filters.pop('organization')
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort is not None and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        return sort


class TopicService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, topic: Topic, index: str = None) -> None:
        self.search_client.index_topic(topic, index)

    def search(self, filters: dict) -> Tuple[List[Topic], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_topics(search_text, offset, page_size, filters, sort)
        results = [Topic.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, topic_id: str) -> Optional[Topic]:
        try:
            return Topic.load_from_dict(self.search_client.find_one_topic(topic_id))
        except TypeError:
            return None

    def delete_one(self, topic_id: str) -> Optional[str]:
        return self.search_client.delete_one_topic(topic_id)

    @staticmethod
    def format_filters(filters):
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort is not None and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        if sort is not None and 'last_modified' in sort:
            sort = sort.replace('last_modified', 'last_modified')
        return sort


class DiscussionService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, discussion: Discussion, index: str = None) -> None:
        self.search_client.index_discussion(discussion, index)

    def search(self, filters: dict) -> Tuple[List[Discussion], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_discussions(search_text, offset, page_size, filters, sort)
        results = [Discussion.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, discussion_id: str) -> Optional[Discussion]:
        try:
            return Discussion.load_from_dict(self.search_client.find_one_discussion(discussion_id))
        except TypeError:
            return None

    def delete_one(self, discussion_id: str) -> Optional[str]:
        return self.search_client.delete_one_discussion(discussion_id)

    @staticmethod
    def format_filters(filters):
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort is not None and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        if sort is not None and 'closed' in sort:
            sort = sort.replace('closed', 'closed_at')
        return sort


class PostService:

    def __init__(self, search_client: ElasticClient):
        self.search_client = search_client

    def feed(self, post: Post, index: str = None) -> None:
        self.search_client.index_post(post, index)

    def search(self, filters: dict) -> Tuple[List[Post], int, int, dict]:
        page = filters.pop('page')
        page_size = filters.pop('page_size')
        search_text = filters.pop('q')
        sort = self.format_sort(filters.pop('sort', None))

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0

        self.format_filters(filters)

        results_number, search_results, facets = self.search_client.query_posts(search_text, offset, page_size, filters, sort)
        results = [Post.load_from_dict(hit) for hit in search_results]
        total_pages = round(results_number / page_size) or 1
        return results, results_number, total_pages, facets

    def find_one(self, post_id: str) -> Optional[Post]:
        try:
            return Post.load_from_dict(self.search_client.find_one_post(post_id))
        except TypeError:
            return None

    def delete_one(self, post_id: str) -> Optional[str]:
        return self.search_client.delete_one_post(post_id)

    @staticmethod
    def format_filters(filters):
        filtered = {k: v for k, v in filters.items() if v is not None}
        filters.clear()
        filters.update(filtered)

    @staticmethod
    def format_sort(sort):
        if sort is not None and 'created' in sort:
            sort = sort.replace('created', 'created_at')
        if sort is not None and 'last_modified' in sort:
            sort = sort.replace('last_modified', 'last_modified')
        if sort is not None and 'published' in sort:
            sort = sort.replace('published', 'published')
        return sort
