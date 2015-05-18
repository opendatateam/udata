# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API, fields

from udata.core.user.api_fields import user_ref_fields

from .forms import DiscussionCreateForm, DiscussionCommentForm
from .models import Message, Discussion
from .permissions import CloseDiscussionPermission
from .signals import on_new_discussion, on_new_discussion_comment, on_discussion_closed

ns = api.namespace('discussions', 'Discussion related operations')

message_fields = api.model('DiscussionMessage', {
    'content': fields.String(description='The message body', required=True),
    'posted_by': fields.Nested(user_ref_fields, description='The message author', required=True),
    'posted_on': fields.ISODateTime(description='The message posting date', required=True),
})

discussion_fields = api.model('Discussion', {
    'id': fields.String(description='The discussion identifier', readonly=True),
    'subject': fields.String(attribute='subject.id', description='The discussion target object identifier', required=True),
    'title': fields.String(description='The discussion title', required=True),
    'user': fields.Nested(user_ref_fields, description='The discussion author', required=True),
    'created': fields.ISODateTime(description='The discussion creation date', readonly=True),
    'closed': fields.ISODateTime(description='The discussion closing date', readonly=True),
    'closed_by': fields.String(attribute='closed_by.id', description='The user who closed the discussion', readonly=True),
    'discussion': fields.Nested(message_fields),
    'url': fields.UrlFor('api.discussion', description='The discussion API URI', readonly=True),
})

comment_discussion_fields = api.model('DiscussionResponse', {
    'comment': fields.String(description='The comment to submit', required=True),
    'close': fields.Boolean(description='Is this a closing response. Only subject owner can close')
})

discussion_page_fields = api.model('DiscussionPage', fields.pager(discussion_fields))

parser = api.parser()
parser.add_argument('closed', type=bool, default=False, location='args', help='Filter closed discussions')
parser.add_argument('for', type=str, location='args', action='append', help='Filter issues for a given subject')
parser.add_argument('page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument('page_size', type=int, default=20, location='args', help='The page size to fetch')


@ns.route('/<id>/', endpoint='discussion')
@api.doc(model=discussion_fields)
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
        '''Add comment and optionnaly close an discussion given its ID'''
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


@ns.route('/', endpoint='discussions')
class DiscussionsAPI(API):
    '''
    Base class for a list of discussions.
    '''
    @api.doc('list_discussions')
    @api.marshal_with(discussion_page_fields)
    @api.doc(parser=parser)
    def get(self):
        '''List all Discussions'''
        args = parser.parse_args()
        discussions = Discussion.objects
        if args['for']:
            discussions = discussions(subject__in=args['for'])
        if not args['closed']:
            discussions = discussions(closed=None)
        return discussions.paginate(args['page'], args['page_size'])

    @api.secure
    @api.expect(discussion_fields)
    @api.doc('create_discussion')
    @api.marshal_with(discussion_fields)
    def post(self):
        '''Create a new Discussion'''
        form = api.validate(DiscussionCreateForm)

        message = Message(
            content=form.comment.data,
            posted_by=current_user.id)
        discussion = Discussion.objects.create(
            subject=form.subject.data.id,
            title=form.title.data,
            user=current_user.id,
            discussion=[message]
        )
        on_new_discussion.send(discussion)

        return discussion, 201
