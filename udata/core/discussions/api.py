# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask_security import current_user
from flask_restplus.inputs import boolean

from udata.auth import admin_permission
from udata.api import api, API, fields
from udata.core.user.api_fields import user_ref_fields

from .forms import DiscussionCreateForm, DiscussionCommentForm
from .models import Message, Discussion
from .permissions import CloseDiscussionPermission
from .signals import (
    on_new_discussion, on_new_discussion_comment, on_discussion_closed,
    on_discussion_deleted
)

ns = api.namespace('discussions', 'Discussion related operations')

message_fields = api.model('DiscussionMessage', {
    'content': fields.String(description='The message body'),
    'posted_by': fields.Nested(user_ref_fields,
                               description='The message author'),
    'posted_on': fields.ISODateTime(description='The message posting date'),
})

discussion_fields = api.model('Discussion', {
    'id': fields.String(description='The discussion identifier'),
    'subject': fields.Nested(api.model_reference,
                             description='The discussion target object'),
    'class': fields.ClassName(description='The object class',
                              discriminator=True),
    'title': fields.String(description='The discussion title'),
    'user': fields.Nested(
        user_ref_fields, description='The discussion author'),
    'created': fields.ISODateTime(description='The discussion creation date'),
    'closed': fields.ISODateTime(description='The discussion closing date'),
    'closed_by': fields.Nested(user_ref_fields, allow_null=True,
                               description='The user who closed the discussion'),
    'discussion': fields.Nested(message_fields),
    'url': fields.UrlFor('api.discussion',
                         description='The discussion API URI'),
    'extras': fields.Raw(description='Extra attributes as key-value pairs'),
})

start_discussion_fields = api.model('DiscussionStart', {
    'title': fields.String(description='The title of the discussion to open',
                           required=True),
    'comment': fields.String(description='The content of the initial comment',
                             required=True),
    'subject': fields.Nested(api.model_reference,
                             description='The discussion target object',
                             required=True),
    'extras': fields.Raw(description='Extras attributes as key-value pairs'),
})

comment_discussion_fields = api.model('DiscussionResponse', {
    'comment': fields.String(
        description='The comment to submit', required=True),
    'close': fields.Boolean(
        description='Is this a closing response. Only subject owner can close')
})

discussion_page_fields = api.model('DiscussionPage',
                                   fields.pager(discussion_fields))

parser = api.parser()
parser.add_argument(
    'sort', type=str, default='-created', location='args',
    help='The sorting attribute')
parser.add_argument(
    'closed', type=boolean, location='args',
    help='Filters discussions on their closed status if specified')
parser.add_argument(
    'for', type=str, location='args', action='append',
    help='Filter discussions for a given subject')
parser.add_argument(
    'page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument(
    'page_size', type=int, default=20, location='args',
    help='The page size to fetch')


@ns.route('/<id>/', endpoint='discussion')
class DiscussionAPI(API):
    '''
    Base class for a discussion thread.
    '''
    @api.doc('get_discussion')
    @api.marshal_with(discussion_fields)
    def get(self, id):
        '''Get a discussion given its ID'''
        discussion = Discussion.objects.get_or_404(id=id)
        return discussion

    @api.secure
    @api.doc('comment_discussion')
    @api.expect(comment_discussion_fields)
    @api.response(403, 'Not allowed to close this discussion')
    @api.marshal_with(discussion_fields)
    def post(self, id):
        '''Add comment and optionally close a discussion given its ID'''
        discussion = Discussion.objects.get_or_404(id=id)
        form = api.validate(DiscussionCommentForm)
        message = Message(
            content=form.comment.data,
            posted_by=current_user.id
        )
        discussion.discussion.append(message)
        close = form.close.data
        if close:
            CloseDiscussionPermission(discussion).test()
            discussion.closed_by = current_user._get_current_object()
            discussion.closed = datetime.now()
        discussion.save()
        if close:
            on_discussion_closed.send(discussion, message=message)
        else:
            on_new_discussion_comment.send(discussion, message=message)
        return discussion

    @api.secure(admin_permission)
    @api.doc('delete_discussion')
    @api.response(403, 'Not allowed to delete this discussion')
    def delete(self, id):
        '''Delete a discussion given its ID'''
        discussion = Discussion.objects.get_or_404(id=id)
        discussion.delete()
        on_discussion_deleted.send(discussion)
        return '', 204


@ns.route('/', endpoint='discussions')
class DiscussionsAPI(API):
    '''
    Base class for a list of discussions.
    '''
    @api.doc('list_discussions', parser=parser)
    @api.marshal_with(discussion_page_fields)
    def get(self):
        '''List all Discussions'''
        args = parser.parse_args()
        discussions = Discussion.objects
        if args['for']:
            discussions = discussions.generic_in(subject=args['for'])
        if args['closed'] is False:
            discussions = discussions(closed=None)
        elif args['closed'] is True:
            discussions = discussions(closed__ne=None)
        discussions = discussions.order_by(args['sort'])
        return discussions.paginate(args['page'], args['page_size'])

    @api.secure
    @api.doc('create_discussion')
    @api.expect(start_discussion_fields)
    @api.marshal_with(discussion_fields)
    def post(self):
        '''Create a new Discussion'''
        form = api.validate(DiscussionCreateForm)

        message = Message(
            content=form.comment.data,
            posted_by=current_user.id)
        discussion = Discussion(user=current_user.id, discussion=[message])
        form.populate_obj(discussion)
        discussion.save()
        on_new_discussion.send(discussion)

        return discussion, 201
