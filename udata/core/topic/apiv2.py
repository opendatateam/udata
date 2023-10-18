import logging

from flask import url_for

from udata.api import apiv2, API, fields
from udata.core.dataset.apiv2 import dataset_page_fields
from udata.core.dataset.models import Dataset
from udata.core.organization.api_fields import org_ref_fields
from udata.core.topic.models import Topic
from udata.core.topic.parsers import TopicApiParser
from udata.core.user.api_fields import user_ref_fields

DEFAULT_SORTING = '-created_at'
DEFAULT_PAGE_SIZE = 50

log = logging.getLogger(__name__)

ns = apiv2.namespace('topics', 'Topics related operations')

topic_parser = TopicApiParser()
datasets_parser = apiv2.page_parser()

common_doc = {
    'params': {'topic': 'The topic ID'}
}

topic_fields = apiv2.model('Topic', {
    'id': fields.String(description='The topic identifier'),
    'name': fields.String(description='The topic name', required=True),
    'slug': fields.String(
        description='The topic permalink string', readonly=True),
    'description': fields.Markdown(
        description='The topic description in Markdown', required=True),
    'tags': fields.List(
        fields.String, description='Some keywords to help in search', required=True),

    'datasets': fields.Raw(attribute=lambda o: {
        'rel': 'subsection',
        'href': url_for('apiv2.dataset_search', topic=o.id, page=1,
                        page_size=DEFAULT_PAGE_SIZE, _external=True),
        'type': 'GET',
        'total': len(o.datasets)
        }, description='Link to the topic datasets'),
    'reuses': fields.Raw(attribute=lambda o: {
        'rel': 'subsection',
        'href': url_for('apiv2.reuse_search', topic=o.id, page=1,
                        page_size=DEFAULT_PAGE_SIZE, _external=True),
        'type': 'GET',
        'total': len(o.reuses)
        }, description='Link to the topic reuses'),
    'featured': fields.Boolean(description='Is the topic featured'),
    'private': fields.Boolean(description='Is the topic private'),
    'created_at': fields.ISODateTime(
        description='The topic creation date', readonly=True),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description='The publishing organization', readonly=True),
    'owner': fields.Nested(
        user_ref_fields, description='The owner user', readonly=True,
        allow_null=True),
    'uri': fields.UrlFor(
        'api.topic', lambda o: {'topic': o},
        description='The topic API URI', readonly=True),
    'page': fields.UrlFor(
        'topics.display', lambda o: {'topic': o},
        description='The topic page URL', readonly=True, fallback_endpoint='api.topic'),
    'extras': fields.Raw(description='Extras attributes as key-value pairs'),
})

topic_page_fields = apiv2.model('TopicPage', fields.pager(topic_fields))


@ns.route('/', endpoint='topics_list', doc=common_doc)
class TopicsAPI(API):
    @apiv2.expect(topic_parser.parser)
    @apiv2.marshal_with(topic_page_fields)
    def get(self):
        '''List all topics'''
        args = topic_parser.parse()
        topics = Topic.objects()
        topics = topic_parser.parse_filters(topics, args)
        sort = args['sort'] or ('$text_score' if args['q'] else None) or DEFAULT_SORTING
        return (topics.order_by(sort)
                .paginate(args['page'], args['page_size']))


@ns.route('/<topic:topic>/', endpoint='topic', doc=common_doc)
@apiv2.response(404, 'Topic not found')
class TopicAPI(API):
    @apiv2.doc('get_topic')
    @apiv2.marshal_with(topic_fields)
    def get(self, topic):
        '''Get a given topic'''
        return topic


@ns.route('/<topic:topic>/datasets/', endpoint='topic_datasets', doc=common_doc)
class TopicDatasetsAPI(API):
    @apiv2.doc('get_topic_datasets')
    @apiv2.expect(datasets_parser)
    @apiv2.marshal_with(dataset_page_fields)
    def get(self, topic):
        '''Get a given topic datasets'''
        args = datasets_parser.parse_args()
        return Dataset.objects.filter(
            id__in=(d.id for d in topic.datasets)
        ).paginate(args['page'], args['page_size'])
