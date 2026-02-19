import click
from datetime import datetime
from fnmatch import fnmatch
import logging
import os
from typing import Tuple, Optional, List

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Date, Document, Float, Integer, Keyword, Text, tokenizer, token_filter, analyzer, query
from elasticsearch_dsl.connections import connections
from udata_search_service.domain.entities import Dataset, Organization, Reuse, Dataservice, Topic, Discussion, Post
from udata_search_service.config import Config
from udata_search_service.infrastructure.utils import IS_TTY

CONSUMER_LOGGING_LEVEL = int(os.environ.get("CONSUMER_LOGGING_LEVEL", logging.INFO))

logging.basicConfig(level=CONSUMER_LOGGING_LEVEL)


# Définition d'un analyzer français (repris ici : https://jolicode.com/blog/construire-un-bon-analyzer-francais-pour-elasticsearch)
# Ajout dans la filtre french_synonym, des synonymes que l'on souhaite implémenter (ex : AMD / Administrateur des Données)
# Création du mapping en indiquant les champs sur lesquels cet analyzer va s'appliquer (title, description, concat, organization)
# et en spécifiant les types de champs que l'on va utiliser pour calculer notre score de pertinence
french_elision = token_filter('french_elision', type='elision', articles_case=True, articles=["l", "m", "t", "qu", "n", "s", "j", "d", "c", "jusqu", "quoiqu", "lorsqu", "puisqu"])
french_stop = token_filter('french_stop', type='stop', stopwords='_french_')
french_stemmer = token_filter('french_stemmer', type='stemmer', language='light_french')
french_synonym = token_filter('french_synonym', type='synonym', ignore_case=True, expand=True, synonyms=Config.SEARCH_SYNONYMS)


dgv_analyzer = analyzer('french_dgv',
                        tokenizer=tokenizer('icu_tokenizer'),
                        filter=['icu_folding', french_elision, french_synonym, french_stemmer, french_stop]
                        )


class IndexDocument(Document):

    @classmethod
    def init_index(cls, es_client: Elasticsearch, suffix: str) -> None:
        alias = cls._index._name
        pattern = alias + '-*'

        logging.info(f'Saving template {alias} on the following pattern: {pattern}')
        index_template = cls._index.as_template(alias, pattern)
        index_template.save()

        if not cls._index.exists():
            logging.info(f'Creating index {alias + suffix}')
            es_client.indices.create(index=alias + suffix)
            es_client.indices.put_alias(index=alias + suffix, name=alias)
        else:
            logging.info(f'Index on alias {alias} already exists')

    @classmethod
    def delete_indices(cls, es_client: Elasticsearch) -> None:
        alias = cls._index._name
        pattern = alias + '*'
        logging.info(f'Deleting indices with pattern {pattern}')
        es_client.indices.delete(index=pattern)

    @classmethod
    def _matches(cls, hit):
        # override _matches to match indices in a pattern instead of just ALIAS
        # hit is the raw dict as returned by elasticsearch
        alias = cls._index._name
        pattern = alias + '-*'
        return fnmatch(hit["_index"], pattern)


class SearchableDataservice(IndexDocument):
    title = Text(analyzer=dgv_analyzer)
    created_at = Date()
    metadata_modified_at = Date()
    tags = Keyword(multi=True)
    topics = Keyword(multi=True)
    badges = Keyword(multi=True)
    organization = Keyword()
    description = Text(analyzer=dgv_analyzer)
    organization_name = Text(analyzer=dgv_analyzer, fields={'keyword': Keyword()})
    organization_with_id = Keyword()
    owner = Keyword()
    views = Float()
    followers = Float()
    description_length = Float()
    access_type = Keyword()
    producer_type = Keyword(multi=True)
    documentation_content = Text(analyzer=dgv_analyzer)

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-dataservice'


class SearchableTopic(IndexDocument):
    name = Text(analyzer=dgv_analyzer)
    description = Text(analyzer=dgv_analyzer)
    tags = Keyword(multi=True)
    featured = Integer()
    private = Integer()
    created_at = Date()
    last_modified = Date()
    organization = Keyword()
    organization_name = Text(analyzer=dgv_analyzer, fields={'keyword': Keyword()})
    organization_with_id = Keyword()
    producer_type = Keyword(multi=True)
    nb_datasets = Integer()
    nb_reuses = Integer()
    nb_dataservices = Integer()

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-topic'


class SearchableDiscussion(IndexDocument):
    title = Text(analyzer=dgv_analyzer)
    content = Text(analyzer=dgv_analyzer)
    created_at = Date()
    closed_at = Date()
    closed = Integer()
    subject_class = Keyword()
    subject_id = Keyword()

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-discussion'


class SearchablePost(IndexDocument):
    name = Text(analyzer=dgv_analyzer)
    headline = Text(analyzer=dgv_analyzer)
    content = Text(analyzer=dgv_analyzer)
    tags = Keyword(multi=True)
    created_at = Date()
    last_modified = Date()
    published = Date()

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-post'


class SearchableOrganization(IndexDocument):
    name = Text(analyzer=dgv_analyzer)
    acronym = Text()
    description = Text(analyzer=dgv_analyzer)
    url = Text()
    orga_sp = Integer()
    created_at = Date()
    followers = Float()
    views = Float()
    reuses = Float()
    datasets = Integer()
    badges = Keyword(multi=True)
    producer_type = Keyword(multi=True)

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-organization'


class SearchableReuse(IndexDocument):
    title = Text(analyzer=dgv_analyzer)
    url = Text()
    created_at = Date()
    last_modified = Date()
    archived = Date()
    orga_followers = Float()
    views = Float()
    followers = Float()
    datasets = Integer()
    featured = Integer()
    type = Keyword()
    topic = Keyword()  # Metadata topic (health, transport, etc.)
    topic_object = Keyword(multi=True)  # Topic objects linked via TopicElement
    tags = Keyword(multi=True)
    badges = Keyword(multi=True)
    organization = Keyword()
    description = Text(analyzer=dgv_analyzer)
    organization_name = Text(analyzer=dgv_analyzer, fields={'keyword': Keyword()})
    organization_with_id = Keyword()
    organization_badges = Keyword(multi=True)
    owner = Keyword()
    producer_type = Keyword(multi=True)

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-reuse'


class SearchableDataset(IndexDocument):
    title = Text(analyzer=dgv_analyzer)
    acronym = Text()
    url = Text()
    created_at = Date()
    last_update = Date()
    tags = Keyword(multi=True)
    license = Keyword()
    badges = Keyword(multi=True)
    frequency = Text()
    format = Keyword(multi=True)
    orga_sp = Integer()
    orga_followers = Float()
    views = Float()
    followers = Float()
    reuses = Float()
    featured = Integer()
    resources_count = Integer()
    resources_ids = Keyword(multi=True)
    resources_titles = Text(analyzer=dgv_analyzer)
    concat_title_org = Text(analyzer=dgv_analyzer)
    temporal_coverage_start = Date()
    temporal_coverage_end = Date()
    granularity = Keyword()
    geozones = Keyword(multi=True)
    description = Text(analyzer=dgv_analyzer)
    organization = Keyword()
    organization_name = Text(analyzer=dgv_analyzer, fields={'keyword': Keyword()})
    organization_with_id = Keyword()
    organization_badges = Keyword(multi=True)
    owner = Keyword()
    schema = Keyword(multi=True)
    topics = Keyword(multi=True)
    access_type = Keyword()
    format_family = Keyword(multi=True)
    producer_type = Keyword(multi=True)

    class Index:
        name = f'{Config.UDATA_INSTANCE_NAME}-dataset'


class ElasticClient:

    def __init__(self, url: str):
        self.es = connections.create_connection(hosts=[url])

    def init_indices(self) -> None:
        '''
        Create templates based on Document mappings and map patterns.
        Create time-based index matchin the template patterns.
        '''
        suffix_name = '-' + datetime.utcnow().strftime('%Y-%m-%d-%H-%M')

        SearchableDataset.init_index(self.es, suffix_name)
        SearchableReuse.init_index(self.es, suffix_name)
        SearchableOrganization.init_index(self.es, suffix_name)
        SearchableDataservice.init_index(self.es, suffix_name)
        SearchableTopic.init_index(self.es, suffix_name)
        SearchableDiscussion.init_index(self.es, suffix_name)
        SearchablePost.init_index(self.es, suffix_name)

    def clean_indices(self) -> None:
        '''
        Removing previous indices and intializing new ones.
        '''

        if IS_TTY:
            msg = 'Indices will be deleted, are you sure?'
            click.confirm(msg, abort=True)
        SearchableDataset.delete_indices(self.es)
        SearchableReuse.delete_indices(self.es)
        SearchableOrganization.delete_indices(self.es)
        SearchableDataservice.delete_indices(self.es)
        SearchableTopic.delete_indices(self.es)
        SearchableDiscussion.delete_indices(self.es)
        SearchablePost.delete_indices(self.es)

        self.init_indices()

    def index_organization(self, to_index: Organization, index: str = None) -> None:
        SearchableOrganization(meta={'id': to_index.id}, **to_index.to_dict()).save(skip_empty=False, index=index)

    def index_dataset(self, to_index: Dataset, index: str = None) -> None:
        data = to_index.to_dict()
        if data.get('organization') and data.get('organization_name'):
            data['organization_with_id'] = f"{data['organization']}|{data['organization_name']}"
        SearchableDataset(meta={'id': to_index.id}, **data).save(skip_empty=False, index=index)

    def index_reuse(self, to_index: Reuse, index: str = None) -> None:
        data = to_index.to_dict()
        if data.get('organization') and data.get('organization_name'):
            data['organization_with_id'] = f"{data['organization']}|{data['organization_name']}"
        SearchableReuse(meta={'id': to_index.id}, **data).save(skip_empty=False, index=index)

    def index_dataservice(self, to_index: Dataservice, index: str = None) -> None:
        data = to_index.to_dict()
        if data.get('organization') and data.get('organization_name'):
            data['organization_with_id'] = f"{data['organization']}|{data['organization_name']}"
        SearchableDataservice(meta={'id': to_index.id}, **data).save(skip_empty=False, index=index)

    def index_topic(self, to_index: Topic, index: str = None) -> None:
        data = to_index.to_dict()
        if data.get('organization') and data.get('organization_name'):
            data['organization_with_id'] = f"{data['organization']}|{data['organization_name']}"
        SearchableTopic(meta={'id': to_index.id}, **data).save(skip_empty=False, index=index)

    def query_organizations(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None) -> Tuple[int, List[dict], dict]:
        search = SearchableOrganization.search()

        post_filters = []
        for key, value in filters.items():
            post_filters.append(query.Q('term', **{key: value}))

        organizations_score_functions = [
            query.SF("field_value_factor", field="orga_sp", factor=8, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="followers", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="views", factor=1, modifier='sqrt', missing=1),
        ]

        if query_text:
            search = search.query('bool', should=[
                    query.Q(
                        'function_score',
                        query=query.Bool(should=[query.MultiMatch(query=query_text, type='phrase', fields=['id^15', 'name^15', 'acronym^15', 'description^8'])]),
                        functions=organizations_score_functions
                    ),
                    query.Q(
                        'function_score',
                        query=query.Bool(should=[query.MultiMatch(
                            query=query_text,
                            type='cross_fields',
                            fields=['id^15', 'name^7', 'acronym^7', 'description^4'],
                            operator="and")]),
                        functions=organizations_score_functions
                    ),
                    query.Match(title={"query": query_text, 'fuzziness': 'AUTO:4,6'}),
            ])
        else:
            search = search.query(query.Q('function_score', query=query.MatchAll(), functions=organizations_score_functions))

        search.aggs.bucket('producer_type', 'terms', field='producer_type', size=50)
        search.aggs.metric('total_count', 'cardinality', field='_id')

        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            search = search.sort(sort, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]

        response = search.execute()
        results_number = response.hits.total.value
        if response.hits and not isinstance(response.hits[0], SearchableOrganization):
            raise ValueError(
                'Results are not of SearchableOrganization type. It probably means that index analyzers '
                'were not correctly set using template patterns on index initialization.'
            )
        res = [hit.to_dict(skip_empty=False) for hit in response.hits]
        
        facets = {}
        if hasattr(response, 'aggregations'):
            total_count = int(response.aggregations.total_count.value) if hasattr(response.aggregations, 'total_count') else 0
            
            for agg_name in ['producer_type']:
                if hasattr(response.aggregations, agg_name):
                    buckets = [
                        {'name': bucket.key, 'count': bucket.doc_count}
                        for bucket in response.aggregations[agg_name].buckets
                    ]
                    facets[agg_name] = [{'name': 'all', 'count': total_count}] + buckets
        
        return results_number, res, facets

    def query_topics(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None) -> Tuple[int, List[dict], dict]:
        search = SearchableTopic.search()

        last_update_range_mapping = {
            'last_30_days': 'now-30d/d',
            'last_12_months': 'now-12M/d',
            'last_3_years': 'now-3y/d',
        }

        # Build filters dictionary by category
        filter_dict = {
            'organization_id_with_name': None,
            'producer_type': None,
            'last_update_range': None,
            'other': []
        }
        
        for key, value in filters.items():
            if key == 'last_update_range':
                if value in last_update_range_mapping:
                    filter_dict['last_update_range'] = query.Q('range', last_modified={'gte': last_update_range_mapping[value]})
            elif key == 'tag':
                if isinstance(value, list):
                    tag_filters = [query.Q('term', tags=tag) for tag in value]
                    filter_dict['other'].append(query.Bool(must=tag_filters))
                else:
                    filter_dict['other'].append(query.Q('term', tags=value))
            elif key == 'organization' and isinstance(value, list):
                list_filters = [query.Q('term', organization=v) for v in value]
                filter_dict['organization_id_with_name'] = query.Bool(should=list_filters, minimum_should_match=1)
            elif key == 'organization_id_with_name' and isinstance(value, list):
                list_filters = [query.Q('term', organization_with_id=v) for v in value]
                filter_dict['organization_id_with_name'] = query.Bool(should=list_filters, minimum_should_match=1)
            elif key == 'organization_id_with_name':
                filter_dict['organization_id_with_name'] = query.Q('term', organization_with_id=value)
            elif key == 'producer_type':
                filter_dict['producer_type'] = query.Q('term', producer_type=value)
            else:
                filter_dict['other'].append(query.Q('term', **{key: value}))

        if query_text:
            search = search.query(
                'bool',
                should=[
                    query.MultiMatch(
                        query=query_text,
                        type='most_fields',
                        operator="and",
                        fields=['id^5', 'name^10', 'description^4', 'tags^3'],
                        fuzziness='AUTO:4,6',
                    )
                ],
            )
        else:
            search = search.query(query.MatchAll())

        def get_filters_except(exclude_key):
            filters_list = filter_dict['other'].copy()
            for key in ['organization_id_with_name', 'producer_type', 'last_update_range']:
                if key != exclude_key and filter_dict[key] is not None:
                    filters_list.append(filter_dict[key])
            return filters_list

        tag_filters = get_filters_except('tag')
        if tag_filters:
            tag_agg = search.aggs.bucket('tag_filtered', 'filter', filter=query.Bool(must=tag_filters))
            tag_agg.bucket('tag', 'terms', field='tags', size=50)
            tag_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('tag', 'terms', field='tags', size=50)
            search.aggs.metric('tag_total', 'cardinality', field='_id')
        
        org_filters = get_filters_except('organization_id_with_name')
        if org_filters:
            org_agg = search.aggs.bucket('organization_id_with_name_filtered', 'filter', filter=query.Bool(must=org_filters))
            org_agg.bucket('organization_id_with_name', 'terms', field='organization_with_id', size=50)
            org_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('organization_id_with_name', 'terms', field='organization_with_id', size=50)
            search.aggs.metric('organization_id_with_name_total', 'cardinality', field='_id')
        
        producer_filters = get_filters_except('producer_type')
        if producer_filters:
            producer_agg = search.aggs.bucket('producer_type_filtered', 'filter', filter=query.Bool(must=producer_filters))
            producer_agg.bucket('producer_type', 'terms', field='producer_type', size=50)
            producer_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('producer_type', 'terms', field='producer_type', size=50)
            search.aggs.metric('producer_type_total', 'cardinality', field='_id')
        
        last_update_filters = get_filters_except('last_update_range')
        if last_update_filters:
            last_update_agg = search.aggs.bucket('last_update_filtered', 'filter', filter=query.Bool(must=last_update_filters))
            last_update_agg.bucket('last_update', 'date_range', field='last_modified', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            last_update_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('last_update', 'date_range', field='last_modified', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            search.aggs.metric('last_update_total', 'cardinality', field='_id')

        post_filters = []
        for key, value in filter_dict.items():
            if key != 'other' and value is not None:
                post_filters.append(value)
        post_filters.extend(filter_dict['other'])

        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            sort_field = sort
            if sort == 'last_update':
                sort_field = 'last_modified'
            elif sort == '-last_update':
                sort_field = '-last_modified'
            search = search.sort(sort_field, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]

        response = search.execute()
        results_number = response.hits.total.value
        if response.hits and not isinstance(response.hits[0], SearchableTopic):
            raise ValueError(
                'Results are not of SearchableTopic type. It probably means that index analyzers were not correctly set '
                'using template patterns on index initialization.'
            )
        res = [hit.to_dict(skip_empty=False) for hit in response.hits]
        
        facets = {}
        if hasattr(response, 'aggregations'):
            facet_configs = [
                ('tag', 'tag_filtered', 'tag_total'),
                ('organization_id_with_name', 'organization_id_with_name_filtered', 'organization_id_with_name_total'),
                ('producer_type', 'producer_type_filtered', 'producer_type_total'),
                ('last_update', 'last_update_filtered', 'last_update_total'),
            ]
            
            for facet_name, filtered_name, total_name in facet_configs:
                if hasattr(response.aggregations, filtered_name):
                    filtered_agg = getattr(response.aggregations, filtered_name)
                    if hasattr(filtered_agg, facet_name):
                        buckets = [
                            {'name': bucket.key, 'count': bucket.doc_count}
                                for bucket in getattr(filtered_agg, facet_name).buckets
                            ]
                        total_count = int(filtered_agg.total.value) if hasattr(filtered_agg, 'total') else 0
                        facets[facet_name] = [{'name': 'all', 'count': total_count}] + buckets
                elif hasattr(response.aggregations, facet_name):
                    buckets = [
                        {'name': bucket.key, 'count': bucket.doc_count}
                        for bucket in getattr(response.aggregations, facet_name).buckets
                    ]
                    total_count = int(getattr(response.aggregations, total_name).value) if hasattr(response.aggregations, total_name) else 0
                    facets[facet_name] = [{'name': 'all', 'count': total_count}] + buckets
        
        return results_number, res, facets

    def query_datasets(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None) -> Tuple[int, List[dict], dict]:
        search = SearchableDataset.search()

        last_update_range_mapping = {
            'last_30_days': 'now-30d/d',
            'last_12_months': 'now-12M/d',
            'last_3_years': 'now-3y/d',
        }

        filter_dict = {
            'format_family': None,
            'access_type': None,
            'producer_type': None,
            'organization_id_with_name': None,
            'last_update_range': None,
            'tag': None,
            'license': None,
            'format': None,
            'schema': None,
            'geozone': None,
            'granularity': None,
            'badge': None,
            'topics': None,
            'other': []
        }
        
        for key, value in filters.items():
            if key == 'temporal_coverage_start':
                filter_dict['other'].append(query.Q('range', temporal_coverage_start={'lte': value}))
            elif key == 'temporal_coverage_end':
                filter_dict['other'].append(query.Q('range', temporal_coverage_end={'gte': value}))
            elif key == 'last_update_range':
                if value in last_update_range_mapping:
                    filter_dict['last_update_range'] = query.Q('range', last_update={'gte': last_update_range_mapping[value]})
            elif key == 'tags':
                tag_filters = [query.Q('term', tags=tag) for tag in value]
                filter_dict['other'].append(query.Bool(must=tag_filters))
            elif key in ['license', 'format', 'schema', 'geozones', 'granularity', 'badges']:
                filter_key = {'geozones': 'geozone', 'badges': 'badge'}.get(key, key)
                if isinstance(value, list):
                    list_filters = [query.Q('term', **{key: v}) for v in value]
                    filter_dict[filter_key] = query.Bool(should=list_filters, minimum_should_match=1)
                else:
                    filter_dict[filter_key] = query.Q('term', **{key: value})
            elif key == 'topics':
                if isinstance(value, list):
                    topic_filters = [query.Q('term', topics=topic) for topic in value]
                    filter_dict['topics'] = query.Bool(should=topic_filters, minimum_should_match=1)
                else:
                    filter_dict['topics'] = query.Q('term', topics=value)
            elif key == 'organization_id_with_name':
                if isinstance(value, list):
                    list_filters = [query.Q('term', organization=v) for v in value]
                    filter_dict[key] = query.Bool(should=list_filters, minimum_should_match=1)
                else:
                    filter_dict[key] = query.Q('term', **{'organization': value})
            elif key in ['format_family', 'access_type', 'producer_type', 'tag']:
                filter_dict[key] = query.Q('term', **{key: value})
            else:
                filter_dict['other'].append(query.Q('term', **{key: value}))

        datasets_score_functions = [
            query.SF("field_value_factor", field="orga_sp", factor=8, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="views", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="followers", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="orga_followers", factor=1, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="featured", factor=1, modifier='sqrt', missing=1),
        ]

        if query_text:
            search = search.query(
                'bool',
                should=[
                    query.Q(
                        'function_score',
                        query=query.Bool(should=[query.MultiMatch(
                            query=query_text,
                            type='phrase',
                            fields=['id^15', 'title^15', 'acronym^15', 'description^8', 'organization_name^8', 'resources_ids^8', 'resources_titles^5']
                        )]),
                        functions=datasets_score_functions
                    ),
                    query.Q(
                        'function_score',
                        query=query.Bool(must=[query.Match(concat_title_org={"query": query_text, "operator": "and", "boost": 8})]),
                        functions=datasets_score_functions,
                    ),
                    query.Q(
                        'function_score',
                        query=query.Bool(should=[query.MultiMatch(
                            query=query_text,
                            type='cross_fields',
                            fields=['id^7', 'title^7', 'acronym^7', 'description^4', 'organization_name^4', 'resources_ids^4', 'resources_titles^2'],
                            operator="and")]),
                        functions=datasets_score_functions
                    ),
                    query.MultiMatch(query=query_text, type='most_fields', operator="and", fields=['title', 'organization_name'], fuzziness='AUTO:4,6')
                ])
        else:
            search = search.query(query.Q('function_score', query=query.MatchAll(), functions=datasets_score_functions))

        def get_filters_except(exclude_key):
            filters_list = filter_dict['other'].copy()
            for key in ['format_family', 'access_type', 'producer_type', 'organization_id_with_name', 'last_update_range', 
                       'tag', 'license', 'format', 'schema', 'geozone', 'granularity', 'topics']:
                if key != exclude_key and filter_dict[key] is not None:
                    filters_list.append(filter_dict[key])
            return filters_list
        
        format_filters = get_filters_except('format_family')
        if format_filters:
            format_agg = search.aggs.bucket('format_family_filtered', 'filter', filter=query.Bool(must=format_filters))
            format_agg.bucket('format_family', 'terms', field='format_family', size=50)
            format_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('format_family', 'terms', field='format_family', size=50)
            search.aggs.metric('format_family_total', 'cardinality', field='_id')
        
        access_filters = get_filters_except('access_type')
        if access_filters:
            access_agg = search.aggs.bucket('access_type_filtered', 'filter', filter=query.Bool(must=access_filters))
            access_agg.bucket('access_type', 'terms', field='access_type', size=50)
            access_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('access_type', 'terms', field='access_type', size=50)
            search.aggs.metric('access_type_total', 'cardinality', field='_id')
        
        producer_filters = get_filters_except('producer_type')
        if producer_filters:
            producer_agg = search.aggs.bucket('producer_type_filtered', 'filter', filter=query.Bool(must=producer_filters))
            producer_agg.bucket('producer_type', 'terms', field='producer_type', size=50)
            producer_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('producer_type', 'terms', field='producer_type', size=50)
            search.aggs.metric('producer_type_total', 'cardinality', field='_id')
        
        org_name_filters = get_filters_except('organization_id_with_name')
        if org_name_filters:
            org_name_agg = search.aggs.bucket('organization_id_with_name_filtered', 'filter', filter=query.Bool(must=org_name_filters))
            org_name_agg.bucket('organization_id_with_name', 'terms', field='organization_with_id', size=50)
            org_name_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('organization_id_with_name', 'terms', field='organization_with_id', size=50)
            search.aggs.metric('organization_id_with_name_total', 'cardinality', field='_id')
        
        last_update_filters = get_filters_except('last_update_range')
        if last_update_filters:
            last_update_agg = search.aggs.bucket('last_update_filtered', 'filter', filter=query.Bool(must=last_update_filters))
            last_update_agg.bucket('last_update', 'date_range', field='last_update', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            last_update_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('last_update', 'date_range', field='last_update', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            search.aggs.metric('last_update_total', 'cardinality', field='_id')
        
        tag_filters = get_filters_except('tag')
        if tag_filters:
            tag_agg = search.aggs.bucket('tag_filtered', 'filter', filter=query.Bool(must=tag_filters))
            tag_agg.bucket('tag', 'terms', field='tags', size=50)
            tag_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('tag', 'terms', field='tags', size=50)
            search.aggs.metric('tag_total', 'cardinality', field='_id')
        
        license_filters = get_filters_except('license')
        if license_filters:
            license_agg = search.aggs.bucket('license_filtered', 'filter', filter=query.Bool(must=license_filters))
            license_agg.bucket('license', 'terms', field='license', size=50)
            license_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('license', 'terms', field='license', size=50)
            search.aggs.metric('license_total', 'cardinality', field='_id')
        
        format_filters = get_filters_except('format')
        if format_filters:
            format_agg = search.aggs.bucket('format_filtered', 'filter', filter=query.Bool(must=format_filters))
            format_agg.bucket('format', 'terms', field='format', size=50)
            format_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('format', 'terms', field='format', size=50)
            search.aggs.metric('format_total', 'cardinality', field='_id')
        
        schema_filters = get_filters_except('schema')
        if schema_filters:
            schema_agg = search.aggs.bucket('schema_filtered', 'filter', filter=query.Bool(must=schema_filters))
            schema_agg.bucket('schema', 'terms', field='schema', size=50)
            schema_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('schema', 'terms', field='schema', size=50)
            search.aggs.metric('schema_total', 'cardinality', field='_id')
        
        geozone_filters = get_filters_except('geozone')
        if geozone_filters:
            geozone_agg = search.aggs.bucket('geozone_filtered', 'filter', filter=query.Bool(must=geozone_filters))
            geozone_agg.bucket('geozone', 'terms', field='geozones', size=50)
            geozone_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('geozone', 'terms', field='geozones', size=50)
            search.aggs.metric('geozone_total', 'cardinality', field='_id')
        
        granularity_filters = get_filters_except('granularity')
        if granularity_filters:
            granularity_agg = search.aggs.bucket('granularity_filtered', 'filter', filter=query.Bool(must=granularity_filters))
            granularity_agg.bucket('granularity', 'terms', field='granularity', size=50)
            granularity_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('granularity', 'terms', field='granularity', size=50)
            search.aggs.metric('granularity_total', 'cardinality', field='_id')
        
        badge_filters = get_filters_except('badge')
        if badge_filters:
            badge_agg = search.aggs.bucket('badge_filtered', 'filter', filter=query.Bool(must=badge_filters))
            badge_agg.bucket('badge', 'terms', field='badges', size=50)
            badge_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('badge', 'terms', field='badges', size=50)
            search.aggs.metric('badge_total', 'cardinality', field='_id')
        
        topics_filters = get_filters_except('topics')
        if topics_filters:
            topics_agg = search.aggs.bucket('topics_filtered', 'filter', filter=query.Bool(must=topics_filters))
            topics_agg.bucket('topics', 'terms', field='topics', size=50)
            topics_agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('topics', 'terms', field='topics', size=50)
            search.aggs.metric('topics_total', 'cardinality', field='_id')

        post_filters = []
        for key, value in filter_dict.items():
            if key != 'other' and value is not None:
                post_filters.append(value)
        post_filters.extend(filter_dict['other'])
        
        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            search = search.sort(sort, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]

        response = search.execute()
        results_number = response.hits.total.value
        if response.hits and not isinstance(response.hits[0], SearchableDataset):
            raise ValueError(
                'Results are not of SearchableDataset type. It probably means that index analyzers were not correctly set '
                'using template patterns on index initialization.'
            )
        res = [hit.to_dict(skip_empty=False) for hit in response.hits]

        facets = {}
        if hasattr(response, 'aggregations'):
            facet_configs = [
                ('format_family', 'format_family_filtered', 'format_family_total'),
                ('access_type', 'access_type_filtered', 'access_type_total'),
                ('producer_type', 'producer_type_filtered', 'producer_type_total'),
                ('organization_id_with_name', 'organization_id_with_name_filtered', 'organization_id_with_name_total'),
                ('last_update', 'last_update_filtered', 'last_update_total'),
                ('tag', 'tag_filtered', 'tag_total'),
                ('license', 'license_filtered', 'license_total'),
                ('format', 'format_filtered', 'format_total'),
                ('schema', 'schema_filtered', 'schema_total'),
                ('geozone', 'geozone_filtered', 'geozone_total'),
                ('granularity', 'granularity_filtered', 'granularity_total'),
                ('badge', 'badge_filtered', 'badge_total'),
                ('topics', 'topics_filtered', 'topics_total'),
            ]
            
            for facet_name, filtered_name, total_name in facet_configs:
                if hasattr(response.aggregations, filtered_name):
                    filtered_agg = getattr(response.aggregations, filtered_name)
                    if hasattr(filtered_agg, facet_name):
                        buckets = [
                            {'name': bucket.key, 'count': bucket.doc_count}
                            for bucket in getattr(filtered_agg, facet_name).buckets
                        ]
                        total_count = int(filtered_agg.total.value) if hasattr(filtered_agg, 'total') else 0
                        facets[facet_name] = [{'name': 'all', 'count': total_count}] + buckets
                elif hasattr(response.aggregations, facet_name):
                    buckets = [
                        {'name': bucket.key, 'count': bucket.doc_count}
                        for bucket in getattr(response.aggregations, facet_name).buckets
                    ]
                    total_count = int(getattr(response.aggregations, total_name).value) if hasattr(response.aggregations, total_name) else 0
                    facets[facet_name] = [{'name': 'all', 'count': total_count}] + buckets

        return results_number, res, facets

    def query_reuses(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None) -> Tuple[int, List[dict], dict]:
        search = SearchableReuse.search()

        last_update_range_mapping = {
            'last_30_days': 'now-30d/d',
            'last_12_months': 'now-12M/d',
            'last_3_years': 'now-3y/d',
        }

        filter_dict = {
            'producer_type': None,
            'organization_id_with_name': None, 
            'topic_object': None,
            'type': None,
            'topic': None,
            'tag': None,
            'badge': None,
            'last_update_range': None,
            'other': []
        }

        # ---- build filters
        for key, value in filters.items():
            if key == 'last_update_range' and value in last_update_range_mapping:
                filter_dict['last_update_range'] = query.Q(
                    'range', last_modified={'gte': last_update_range_mapping[value]}
                )

            elif key == 'tags':
                if isinstance(value, list):
                    tag_filters = [query.Q('term', tags=v) for v in value]
                    filter_dict['other'].append(query.Bool(must=tag_filters))
                else:
                    filter_dict['tag'] = query.Q('term', tags=value)

            elif key == 'tag':
                filter_dict['tag'] = query.Q('term', tags=value)

            elif key == 'badges':
                if isinstance(value, list):
                    badge_filters = [query.Q('term', badges=v) for v in value]
                    filter_dict['badge'] = query.Bool(should=badge_filters, minimum_should_match=1)
                else:
                    filter_dict['badge'] = query.Q('term', badges=value)

            elif key == 'badge':
                filter_dict['badge'] = query.Q('term', badges=value)

            elif key == 'topic_object':
                if isinstance(value, list):
                    topic_filters = [query.Q('term', topic_object=v) for v in value]
                    filter_dict['topic_object'] = query.Bool(should=topic_filters, minimum_should_match=1)
                else:
                    filter_dict['topic_object'] = query.Q('term', topic_object=value)

            elif key == 'organization_id_with_name':
                if isinstance(value, list):
                    org_filters = [query.Q('term', organization=v) for v in value]
                    filter_dict[key] = query.Bool(should=org_filters, minimum_should_match=1)
                else:
                    filter_dict[key] = query.Q('term', organization=value)

            elif key == 'organization':
                if isinstance(value, list):
                    org_filters = [query.Q('term', organization=v) for v in value]
                    filter_dict['other'].append(query.Bool(should=org_filters, minimum_should_match=1))
                else:
                    filter_dict['other'].append(query.Q('term', organization=value))

            elif key in ['producer_type', 'type', 'topic']:
                filter_dict[key] = query.Q('term', **{key: value})

            else:
                filter_dict['other'].append(query.Q('term', **{key: value}))

        reuses_score_functions = [
            query.SF("field_value_factor", field="views", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="followers", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="orga_followers", factor=1, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="featured", factor=1, modifier='sqrt', missing=1),
            query.SF("script_score", script={"source": "doc['archived'].size() == 0 ? 1 : 0.2"}),
        ]

        if query_text:
            search = search.query('bool', should=[
                query.Q(
                    'function_score',
                    query=query.Bool(should=[query.MultiMatch(
                        query=query_text,
                        type='phrase',
                        fields=['id^15', 'title^15', 'description^8', 'organization_name^8']
                    )]),
                    functions=reuses_score_functions
                ),
                query.Q(
                    'function_score',
                    query=query.Bool(should=[query.MultiMatch(
                        query=query_text,
                        type='cross_fields',
                        fields=['id^7', 'title^7', 'description^4', 'organization_name^4'],
                        operator="and"
                    )]),
                    functions=reuses_score_functions
                ),
                query.MultiMatch(
                    query=query_text,
                    type='most_fields',
                    operator="and",
                    fields=['title', 'organization_name'],
                    fuzziness='AUTO:4,6'
                ),
            ])
        else:
            search = search.query(query.Q('function_score', query=query.MatchAll(), functions=reuses_score_functions))

        def get_filters_except(exclude_key: str):
            flt = list(filter_dict['other'])
            for k in ['producer_type', 'organization_id_with_name', 'topic_object', 'type', 'topic', 'tag', 'badge', 'last_update_range']:
                if k != exclude_key and filter_dict[k] is not None:
                    flt.append(filter_dict[k])
            return flt

        facet_fields = {
            'producer_type': ('producer_type', 'producer_type'),
            'organization_id_with_name': ('organization_with_id', 'organization_id_with_name'),
            'topic': ('topic', 'topic'),
            'type': ('type', 'type'),
            'tag': ('tags', 'tag'),
            'badge': ('badges', 'badge'),
        }

        for facet_key, (es_field, agg_name) in facet_fields.items():
            f = get_filters_except(facet_key)
            if f:
                agg = search.aggs.bucket(f'{agg_name}_filtered', 'filter', filter=query.Bool(must=f))
                agg.bucket(agg_name, 'terms', field=es_field, size=50)
                agg.metric('total', 'cardinality', field='_id')
            else:
                search.aggs.bucket(agg_name, 'terms', field=es_field, size=50)
                search.aggs.metric(f'{agg_name}_total', 'cardinality', field='_id')

        f = get_filters_except('last_update_range')
        if f:
            agg = search.aggs.bucket('last_update_filtered', 'filter', filter=query.Bool(must=f))
            agg.bucket('last_update', 'date_range', field='last_modified', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('last_update', 'date_range', field='last_modified', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            search.aggs.metric('last_update_total', 'cardinality', field='_id')

        post_filters = []
        for k in ['producer_type', 'organization_id_with_name', 'topic_object', 'type', 'topic', 'tag', 'badge', 'last_update_range']:
            if filter_dict[k] is not None:
                post_filters.append(filter_dict[k])
        post_filters.extend(filter_dict['other'])
        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            search = search.sort(sort, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]
        response = search.execute()

        results_number = response.hits.total.value
        if response.hits and not isinstance(response.hits[0], SearchableReuse):
            raise ValueError(
                'Results are not of SearchableReuse type. It probably means that index analyzers were not correctly set '
                'using template patterns on index initialization.'
            )

        res = [hit.to_dict(skip_empty=False) for hit in response.hits]

        facets = {}

        for facet_key, (_, agg_name) in facet_fields.items():
            filtered_name = f'{agg_name}_filtered'
            total_name = f'{agg_name}_total'

            if hasattr(response.aggregations, filtered_name):
                fa = getattr(response.aggregations, filtered_name)
                buckets = [{'name': b.key, 'count': b.doc_count} for b in getattr(fa, agg_name).buckets]
                total = int(fa.total.value) if hasattr(fa, 'total') else 0
                facets[agg_name] = [{'name': 'all', 'count': total}] + buckets

            elif hasattr(response.aggregations, agg_name):
                buckets = [{'name': b.key, 'count': b.doc_count} for b in getattr(response.aggregations, agg_name).buckets]
                total = int(getattr(response.aggregations, total_name).value) if hasattr(response.aggregations, total_name) else 0
                facets[agg_name] = [{'name': 'all', 'count': total}] + buckets

        if hasattr(response.aggregations, 'last_update_filtered'):
            fa = response.aggregations.last_update_filtered
            buckets = [{'name': b.key, 'count': b.doc_count} for b in fa.last_update.buckets]
            total = int(fa.total.value) if hasattr(fa, 'total') else 0
            facets['last_update'] = [{'name': 'all', 'count': total}] + buckets
        elif hasattr(response.aggregations, 'last_update'):
            buckets = [{'name': b.key, 'count': b.doc_count} for b in response.aggregations.last_update.buckets]
            total = int(response.aggregations.last_update_total.value) if hasattr(response.aggregations, 'last_update_total') else 0
            facets['last_update'] = [{'name': 'all', 'count': total}] + buckets

        return results_number, res, facets

 
    def query_dataservices(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None):
        search = SearchableDataservice.search()

        last_update_range_mapping = {
            'last_30_days': 'now-30d/d',
            'last_12_months': 'now-12M/d',
            'last_3_years': 'now-3y/d',
        }

        filter_dict = {
            'access_type': None,
            'producer_type': None,
            'organization_id_with_name': None,
            'topics': None,
            'tag': None,
            'badge': None,
            'last_update_range': None,
            'other': []
        }

        for key, value in filters.items():
            if key == 'last_update_range' and value in last_update_range_mapping:
                filter_dict['last_update_range'] = query.Q('range', metadata_modified_at={'gte': last_update_range_mapping[value]})

            elif key == 'tags':
                if isinstance(value, list):
                    tag_filters = [query.Q('term', tags=v) for v in value]
                    filter_dict['other'].append(query.Bool(must=tag_filters))
                else:
                    filter_dict['tag'] = query.Q('term', tags=value)

            elif key == 'tag':
                filter_dict['tag'] = query.Q('term', tags=value)

            elif key == 'topics':
                if isinstance(value, list):
                    topic_filters = [query.Q('term', topics=v) for v in value]
                    filter_dict['topics'] = query.Bool(should=topic_filters, minimum_should_match=1)
                else:
                    filter_dict['topics'] = query.Q('term', topics=value)

            elif key == 'organization_id_with_name':
                if isinstance(value, list):
                    org_filters = [query.Q('term', organization=v) for v in value]
                    filter_dict[key] = query.Bool(should=org_filters, minimum_should_match=1)
                else:
                    filter_dict[key] = query.Q('term', organization=value)

            elif key == 'producer_type':
                filter_dict['producer_type'] = query.Q('term', producer_type=value)

            elif key == 'access_type':
                filter_dict['access_type'] = query.Q('term', access_type=value)

            elif key in ('badge', 'badges'):
                if isinstance(value, list):
                    badge_filters = [query.Q('term', badges=v) for v in value]
                    filter_dict['badge'] = query.Bool(should=badge_filters, minimum_should_match=1)
                else:
                    filter_dict['badge'] = query.Q('term', badges=value)

            else:
                filter_dict['other'].append(query.Q('term', **{key: value}))

        dataservices_score_functions = [
            query.SF("field_value_factor", field="description_length", factor=1, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="views", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="followers", factor=4, modifier='sqrt', missing=1),
            query.SF("field_value_factor", field="orga_followers", factor=1, modifier='sqrt', missing=1),
        ]

        if query_text:
            search = search.query('bool', should=[
                query.Q(
                    'function_score',
                    query=query.Bool(should=[query.MultiMatch(
                        query=query_text,
                        type='phrase',
                        fields=['id^15', 'title^15', 'description^8', 'organization_name^8', 'documentation_content^3']
                    )]),
                    functions=dataservices_score_functions
                ),
                query.Q(
                    'function_score',
                    query=query.Bool(should=[query.MultiMatch(
                        query=query_text,
                        type='cross_fields',
                        fields=['id^7', 'title^7', 'description^4', 'organization_name^4', 'documentation_content^2'],
                        operator="and"
                    )]),
                    functions=dataservices_score_functions
                ),
                query.MultiMatch(
                    query=query_text,
                    type='most_fields',
                    operator="and",
                    fields=['title', 'organization_name', 'documentation_content'],
                    fuzziness='AUTO:4,6'
                )
            ])
        else:
            search = search.query(query.Q('function_score', query=query.MatchAll(), functions=dataservices_score_functions))

        def get_filters_except(exclude_key: str):
            filters_list = list(filter_dict['other'])
            for k in ['access_type', 'producer_type', 'organization_id_with_name', 'topics', 'tag', 'badge', 'last_update_range']:
                if k != exclude_key and filter_dict[k] is not None:
                    filters_list.append(filter_dict[k])
            return filters_list

        facet_fields = {
            'access_type': ('access_type', 'access_type'),
            'producer_type': ('producer_type', 'producer_type'),
            'organization_id_with_name': ('organization_with_id', 'organization_id_with_name'),
            'tag': ('tags', 'tag'),
            'badge': ('badges', 'badge'),
        }

        for facet_name, (es_field, agg_name) in facet_fields.items():
            f = get_filters_except(facet_name)
            if f:
                agg = search.aggs.bucket(f'{agg_name}_filtered', 'filter', filter=query.Bool(must=f))
                agg.bucket(agg_name, 'terms', field=es_field, size=50)
                agg.metric('total', 'cardinality', field='_id')
            else:
                search.aggs.bucket(agg_name, 'terms', field=es_field, size=50)
                search.aggs.metric(f'{agg_name}_total', 'cardinality', field='_id')

        # last_update facet
        f = get_filters_except('last_update_range')
        if f:
            agg = search.aggs.bucket('last_update_filtered', 'filter', filter=query.Bool(must=f))
            agg.bucket('last_update', 'date_range', field='metadata_modified_at', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            agg.metric('total', 'cardinality', field='_id')
        else:
            search.aggs.bucket('last_update', 'date_range', field='metadata_modified_at', ranges=[
                {'key': 'last_30_days', 'from': 'now-30d/d'},
                {'key': 'last_12_months', 'from': 'now-12M/d'},
                {'key': 'last_3_years', 'from': 'now-3y/d'},
            ])
            search.aggs.metric('last_update_total', 'cardinality', field='_id')

        post_filters = []
        for k in ['access_type', 'producer_type', 'organization_id_with_name', 'topics', 'tag', 'badge', 'last_update_range']:
            if filter_dict[k] is not None:
                post_filters.append(filter_dict[k])
        post_filters.extend(filter_dict['other'])
        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            search = search.sort(sort, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]
        response = search.execute()

        results_number = response.hits.total.value
        res = [hit.to_dict(skip_empty=False) for hit in response.hits]

        facets = {}
        for facet_name, (_, agg_name) in facet_fields.items():
            filtered_name = f'{agg_name}_filtered'
            total_name = f'{agg_name}_total'
            if hasattr(response.aggregations, filtered_name):
                fa = getattr(response.aggregations, filtered_name)
                buckets = [{'name': b.key, 'count': b.doc_count} for b in getattr(fa, agg_name).buckets]
                total = int(fa.total.value) if hasattr(fa, 'total') else 0
                facets[agg_name] = [{'name': 'all', 'count': total}] + buckets
            elif hasattr(response.aggregations, agg_name):
                buckets = [{'name': b.key, 'count': b.doc_count} for b in getattr(response.aggregations, agg_name).buckets]
                total = int(getattr(response.aggregations, total_name).value) if hasattr(response.aggregations, total_name) else 0
                facets[agg_name] = [{'name': 'all', 'count': total}] + buckets

        if hasattr(response.aggregations, 'last_update_filtered'):
            fa = response.aggregations.last_update_filtered
            buckets = [{'name': b.key, 'count': b.doc_count} for b in fa.last_update.buckets]
            total = int(fa.total.value) if hasattr(fa, 'total') else 0
            facets['last_update'] = [{'name': 'all', 'count': total}] + buckets
        elif hasattr(response.aggregations, 'last_update'):
            buckets = [{'name': b.key, 'count': b.doc_count} for b in response.aggregations.last_update.buckets]
            total = int(response.aggregations.last_update_total.value) if hasattr(response.aggregations, 'last_update_total') else 0
            facets['last_update'] = [{'name': 'all', 'count': total}] + buckets

        return results_number, res, facets



    def find_one_organization(self, organization_id: str) -> Optional[dict]:
        try:
            return SearchableOrganization.get(id=organization_id).to_dict()
        except NotFoundError:
            return None

    def find_one_dataset(self, dataset_id: str) -> Optional[dict]:
        try:
            return SearchableDataset.get(id=dataset_id).to_dict()
        except NotFoundError:
            return None

    def find_one_reuse(self, reuse_id: str) -> Optional[dict]:
        try:
            return SearchableReuse.get(id=reuse_id).to_dict()
        except NotFoundError:
            return None

    def find_one_dataservice(self, dataservice_id: str) -> Optional[dict]:
        try:
            return SearchableDataservice.get(id=dataservice_id).to_dict()
        except NotFoundError:
            return None

    def find_one_topic(self, topic_id: str) -> Optional[dict]:
        try:
            return SearchableTopic.get(id=topic_id).to_dict()
        except NotFoundError:
            return None

    def delete_one_organization(self, organization_id: str) -> Optional[str]:
        try:
            SearchableOrganization.get(id=organization_id).delete()
            return organization_id
        except NotFoundError:
            return None

    def delete_one_dataset(self, dataset_id: str) -> Optional[str]:
        try:
            SearchableDataset.get(id=dataset_id).delete()
            return dataset_id
        except NotFoundError:
            return None

    def delete_one_reuse(self, reuse_id: str) -> Optional[str]:
        try:
            SearchableReuse.get(id=reuse_id).delete()
            return reuse_id
        except NotFoundError:
            return None

    def delete_one_dataservice(self, dataservice_id: str) -> Optional[str]:
        try:
            SearchableDataservice.get(id=dataservice_id).delete()
            return dataservice_id
        except NotFoundError:
            return None

    def delete_one_topic(self, topic_id: str) -> Optional[str]:
        try:
            SearchableTopic.get(id=topic_id).delete()
            return topic_id
        except NotFoundError:
            return None

    def index_discussion(self, to_index: Discussion, index: str = None) -> None:
        SearchableDiscussion(meta={'id': to_index.id}, **to_index.to_dict()).save(skip_empty=False, index=index)

    def query_discussions(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None) -> Tuple[int, List[dict], dict]:
        search = SearchableDiscussion.search()

        last_update_range_mapping = {
            'last_30_days': 'now-30d/d',
            'last_12_months': 'now-12M/d',
            'last_3_years': 'now-3y/d',
        }

        post_filters = []
        
        for key, value in filters.items():
            if key == 'last_update_range':
                if value in last_update_range_mapping:
                    post_filters.append(query.Q('range', created_at={'gte': last_update_range_mapping[value]}))
            elif key == 'object_type':
                post_filters.append(query.Q('term', subject_class=value))
            else:
                post_filters.append(query.Q('term', **{key: value}))

        if query_text:
            search = search.query(
                'bool',
                should=[
                    query.MultiMatch(
                        query=query_text,
                        type='most_fields',
                        operator="and",
                        fields=['id^5', 'title^10', 'content^4'],
                        fuzziness='AUTO:4,6',
                    )
                ],
            )
        else:
            search = search.query(query.MatchAll())

        search.aggs.bucket('object_type', 'terms', field='subject_class', size=50)
        search.aggs.bucket('last_update', 'date_range', field='created_at', ranges=[
            {'key': 'last_30_days', 'from': 'now-30d/d'},
            {'key': 'last_12_months', 'from': 'now-12M/d'},
            {'key': 'last_3_years', 'from': 'now-3y/d'},
        ])
        search.aggs.metric('total_count', 'cardinality', field='_id')

        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            search = search.sort(sort, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]

        response = search.execute()
        results_number = response.hits.total.value
        if response.hits and not isinstance(response.hits[0], SearchableDiscussion):
            raise ValueError(
                'Results are not of SearchableDiscussion type. It probably means that index analyzers were not correctly set '
                'using template patterns on index initialization.'
            )
        res = [hit.to_dict(skip_empty=False) for hit in response.hits]

        facets = {}
        if hasattr(response, 'aggregations'):
            total_count = int(response.aggregations.total_count.value) if hasattr(response.aggregations, 'total_count') else 0
            
            for agg_name in ['object_type', 'last_update']:
                if hasattr(response.aggregations, agg_name):
                    buckets = [
                        {'name': bucket.key, 'count': bucket.doc_count}
                        for bucket in response.aggregations[agg_name].buckets
                    ]
                    facets[agg_name] = [{'name': 'all', 'count': total_count}] + buckets

        return results_number, res, facets

    def find_one_discussion(self, discussion_id: str) -> Optional[dict]:
        try:
            return SearchableDiscussion.get(id=discussion_id).to_dict()
        except NotFoundError:
            return None

    def delete_one_discussion(self, discussion_id: str) -> Optional[str]:
        try:
            SearchableDiscussion.get(id=discussion_id).delete()
            return discussion_id
        except NotFoundError:
            return None

    def index_post(self, to_index: Post, index: str = None) -> None:
        SearchablePost(meta={'id': to_index.id}, **to_index.to_dict()).save(skip_empty=False, index=index)

    def query_posts(self, query_text: str, offset: int, page_size: int, filters: dict, sort: Optional[str] = None) -> Tuple[int, List[dict], dict]:
        search = SearchablePost.search()

        last_modified_range_mapping = {
            'last_30_days': 'now-30d/d',
            'last_12_months': 'now-12M/d',
            'last_3_years': 'now-3y/d',
        }

        post_filters = []
        
        for key, value in filters.items():
            if key == 'last_update_range':
                if value in last_modified_range_mapping:
                    post_filters.append(query.Q('range', last_modified={'gte': last_modified_range_mapping[value]}))
            elif key == 'tags':
                if isinstance(value, list):
                    tag_filters = [query.Q('term', tags=tag) for tag in value]
                    post_filters.append(query.Bool(must=tag_filters))
                else:
                    post_filters.append(query.Q('term', tags=value))
            else:
                post_filters.append(query.Q('term', **{key: value}))

        if query_text:
            search = search.query(
                'bool',
                should=[
                    query.MultiMatch(
                        query=query_text,
                        type='most_fields',
                        operator="and",
                        fields=['id^5', 'name^10', 'headline^7', 'content^4', 'tags^3'],
                        fuzziness='AUTO:4,6',
                    )
                ],
            )
        else:
            search = search.query(query.MatchAll())

        search.aggs.bucket('last_update', 'date_range', field='last_modified', ranges=[
            {'key': 'last_30_days', 'from': 'now-30d/d'},
            {'key': 'last_12_months', 'from': 'now-12M/d'},
            {'key': 'last_3_years', 'from': 'now-3y/d'},
        ])
        search.aggs.metric('total_count', 'cardinality', field='_id')

        if post_filters:
            search = search.post_filter(query.Bool(must=post_filters))

        if sort:
            search = search.sort(sort, {'_score': {'order': 'desc'}})

        search = search[offset:(offset + page_size)]

        response = search.execute()
        results_number = response.hits.total.value
        if response.hits and not isinstance(response.hits[0], SearchablePost):
            raise ValueError(
                'Results are not of SearchablePost type. It probably means that index analyzers were not correctly set '
                'using template patterns on index initialization.'
            )
        res = [hit.to_dict(skip_empty=False) for hit in response.hits]

        facets = {}
        if hasattr(response, 'aggregations'):
            total_count = int(response.aggregations.total_count.value) if hasattr(response.aggregations, 'total_count') else 0
            
            for agg_name in ['last_update']:
                if hasattr(response.aggregations, agg_name):
                    buckets = [
                        {'name': bucket.key, 'count': bucket.doc_count}
                        for bucket in response.aggregations[agg_name].buckets
                    ]
                    facets[agg_name] = [{'name': 'all', 'count': total_count}] + buckets

        return results_number, res, facets

    def find_one_post(self, post_id: str) -> Optional[dict]:
        try:
            return SearchablePost.get(id=post_id).to_dict()
        except NotFoundError:
            return None

    def delete_one_post(self, post_id: str) -> Optional[str]:
        try:
            SearchablePost.get(id=post_id).delete()
            return post_id
        except NotFoundError:
            return None
