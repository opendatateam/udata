from udata.api import api, fields, API
from udata.core.dataset.api_fields import dataset_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.reuse.api_fields import reuse_fields
from udata.core.topic.permissions import TopicEditPermission
from udata.core.topic.parsers import TopicApiParser
from udata.core.user.api_fields import user_ref_fields

from .models import Topic
from .forms import TopicForm

DEFAULT_SORTING = '-created_at'

ns = api.namespace('topics', 'Topics related operations')

topic_fields = api.model('Topic', {
    'id': fields.String(description='The topic identifier'),
    'name': fields.String(description='The topic name', required=True),
    'slug': fields.String(
        description='The topic permalink string', readonly=True),
    'description': fields.Markdown(
        description='The topic description in Markdown', required=True),
    'tags': fields.List(
        fields.String, description='Some keywords to help in search', required=True),
    'datasets': fields.List(
        fields.Nested(dataset_fields),
        description='The topic datasets',
        attribute=lambda o: [d.fetch() for d in o.datasets],
    ),
    'reuses': fields.List(
        fields.Nested(reuse_fields),
        description='The topic reuses',
        attribute=lambda o: [r.fetch() for r in o.reuses],
    ),
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
}, mask='*,datasets{id,title,uri,page},reuses{id,title,image,image_thumbnail,uri,page}')

topic_page_fields = api.model('TopicPage', fields.pager(topic_fields))

topic_parser = TopicApiParser()


@ns.route('/', endpoint='topics')
class TopicsAPI(API):
    """
    Warning: querying a list with a topic containing a lot of related objects (datasets, reuses)
    will fail/take a lot of time because every object is dereferenced. Use api v2 if you can.
    """

    @api.doc('list_topics')
    @api.expect(topic_parser.parser)
    @api.marshal_with(topic_page_fields)
    def get(self):
        '''List all topics'''
        args = topic_parser.parse()
        topics = Topic.objects()
        topics = topic_parser.parse_filters(topics, args)
        sort = args['sort'] or ('$text_score' if args['q'] else None) or DEFAULT_SORTING
        return (topics.order_by(sort)
                .paginate(args['page'], args['page_size']))

    @api.doc('create_topic')
    @api.expect(topic_fields)
    @api.marshal_with(topic_fields)
    @api.response(400, 'Validation error')
    def post(self):
        '''Create a topic'''
        form = api.validate(TopicForm)
        return form.save(), 201


@ns.route('/<topic:topic>/', endpoint='topic')
@api.param('topic', 'The topic ID or slug')
@api.response(404, 'Object not found')
class TopicAPI(API):
    """
    Warning: querying a topic containing a lot of related objects (datasets, reuses)
    will fail/take a lot of time because every object is dereferenced. Use api v2 if you can.
    """

    @api.doc('get_topic')
    @api.marshal_with(topic_fields)
    def get(self, topic):
        '''Get a given topic'''
        return topic

    @api.secure
    @api.doc('update_topic')
    @api.expect(topic_fields)
    @api.marshal_with(topic_fields)
    @api.response(400, 'Validation error')
    @api.response(403, 'Forbidden')
    def put(self, topic):
        '''Update a given topic'''
        if not TopicEditPermission(topic).can():
            api.abort(403, 'Forbidden')
        form = api.validate(TopicForm, topic)
        return form.save()

    @api.secure
    @api.doc('delete_topic')
    @api.response(204, 'Object deleted')
    @api.response(403, 'Forbidden')
    def delete(self, topic):
        '''Delete a given topic'''
        if not TopicEditPermission(topic).can():
            api.abort(403, 'Forbidden')
        topic.delete()
        return '', 204
