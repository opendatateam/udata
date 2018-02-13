# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, fields, API
from udata.auth import admin_permission


from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.api_fields import reuse_fields
from udata.core.user.api_fields import user_ref_fields

from .models import Topic
from .forms import TopicForm

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
        fields.Nested(dataset_fields), description='The topic datasets'),
    'reuses': fields.List(
        fields.Nested(reuse_fields), description='The topic reuses'),
    'featured': fields.Boolean(description='Is the topic featured'),
    'private': fields.Boolean(description='Is the topic private'),
    'created_at': fields.ISODateTime(
        description='The topic creation date', readonly=True),
    'last_modified': fields.ISODateTime(
        description='The topic last modification date', readonly=True),
    'deleted': fields.ISODateTime(
        description='The organization identifier', readonly=True),
    'owner': fields.Nested(
        user_ref_fields, description='The owner user', readonly=True,
        allow_null=True),
    'uri': fields.UrlFor(
        'api.topic', lambda o: {'topic': o},
        description='The topic API URI', readonly=True),
    'page': fields.UrlFor(
        'topics.display', lambda o: {'topic': o},
        description='The topic page URL', readonly=True),
}, mask='*,datasets{id,title,uri,page},reuses{id,title, image, image_thumbnail,uri,page}')


topic_page_fields = api.model('TopicPage', fields.pager(topic_fields))

parser = api.page_parser()


@ns.route('/', endpoint='topics')
class TopicsAPI(API):

    @api.doc('list_topics', model=topic_page_fields, parser=parser)
    @api.marshal_with(topic_page_fields)
    def get(self):
        '''List all topics'''
        args = parser.parse_args()
        return (Topic.objects.order_by('-created')
                             .paginate(args['page'], args['page_size']))

    @api.doc('create_topic', responses={400: 'Validation error'})
    @api.secure(admin_permission)
    @api.expect(topic_fields)
    @api.marshal_with(topic_fields)
    def post(self):
        '''Create a topic'''
        form = api.validate(TopicForm)
        return form.save(), 201


@ns.route('/<topic:topic>/', endpoint='topic')
@api.doc(responses={404: 'Object not found'})
@api.doc(params={'topic': 'The topic ID or slug'})
class TopicAPI(API):
    @api.doc('get_topic')
    @api.marshal_with(topic_fields)
    def get(self, topic):
        '''Get a given topic'''
        return topic

    @api.secure(admin_permission)
    @api.expect(topic_fields)
    @api.marshal_with(topic_fields)
    @api.doc('update_topic', responses={400: 'Validation error'})
    def put(self, topic):
        '''Update a given topic'''
        form = api.validate(TopicForm, topic)
        return form.save()

    @api.secure(admin_permission)
    @api.doc('delete_topic', model=None, responses={204: 'Object deleted'})
    def delete(self, topic):
        '''Delete a given topic'''
        topic.delete()
        return '', 204
