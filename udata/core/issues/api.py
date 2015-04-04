# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API, marshal, fields

from udata.core.user.api_fields import user_ref_fields

from .forms import IssueCreateForm, IssueCommentForm
from .models import Issue, Message, ISSUE_TYPES
from .signals import on_new_issue, on_new_issue_comment, on_issue_closed

ns = api.namespace('issues', 'Issue related operations')

message_fields = api.model('IssueMessage', {
    'content': fields.String(description='The message body', required=True),
    'posted_by': fields.Nested(user_ref_fields, description='The message author', required=True),
    'posted_on': fields.ISODateTime(description='The message posting date', required=True),
})

issue_fields = api.model('Issue', {
    'id': fields.String(description='The issue identifier', readonly=True),
    'type': fields.String(description='The issue type', required=True, enum=ISSUE_TYPES.keys()),
    'subject': fields.String(attribute='subject.id', description='The issue target object identifier', required=True),
    'user': fields.Nested(user_ref_fields, description='The issue author', required=True),
    'created': fields.ISODateTime(description='The issue creation date', readonly=True),
    'closed': fields.ISODateTime(description='The issue closing date', readonly=True),
    'closed_by': fields.String(attribute='closed_by.id', description='The user who closed the issue', readonly=True),
    'discussion': fields.Nested(message_fields),
    'url': fields.UrlFor('api.issue', description='The issue API URI', readonly=True),
})

issue_page_fields = api.model('IssuePage', fields.pager(issue_fields))

parser = api.parser()
parser.add_argument('closed', type=bool, default=False, location='args', help='Filter closed issues')
parser.add_argument('page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument('page_size', type=int, default=20, location='args', help='The page size to fetch')


@ns.route('/for/<id>/', endpoint='issues_for')
class IssuesAPI(API):
    '''
    Base Issues Model API (Create and list).
    '''
    model = Issue

    @api.secure
    @api.doc(model=issue_fields)
    @api.doc(id='create_issue')
    def post(self, id):
        '''Create a new Issue for an object given its ID'''
        form = api.validate(IssueCreateForm)

        message = Message(content=form.comment.data, posted_by=current_user.id)
        issue = self.model.objects.create(
            subject=id,
            type=form.type.data,
            user=current_user.id,
            discussion=[message]
        )
        on_new_issue.send(issue)

        return marshal(issue, issue_fields), 201

    @api.doc(id='list_issues_for', parser=parser)
    @api.marshal_with(issue_page_fields)
    def get(self, id):
        '''List all Issues for an object given its ID'''
        args = parser.parse_args()
        issues = self.model.objects(subject=id)
        if not args['closed']:
            issues = issues(closed=None)
        return issues.paginate(args['page'], args['page_size'])


@ns.route('/<id>/', endpoint='issue')
@api.doc(model=issue_fields)
class IssueAPI(API):
    '''
    Single Issue Model API (Read and update).
    '''

    @api.doc(id='get_issue')
    def get(self, id):
        '''Get an issue given its ID'''
        issue = Issue.objects.get_or_404(id=id)
        return marshal(issue, issue_fields)

    @api.secure
    @api.doc(id='comment_issue')
    def post(self, id):
        '''Add comment and optionnaly close an issue given its ID'''
        issue = Issue.objects.get_or_404(id=id)
        form = api.validate(IssueCommentForm)
        message = Message(
            content=form.comment.data,
            posted_by=current_user.id
        )
        issue.discussion.append(message)
        close = form.close.data
        if close:
            issue.closed_by = current_user._get_current_object()
            issue.closed = datetime.now()
        issue.save()
        if close:
            on_issue_closed.send(issue, message=message)
        else:
            on_new_issue_comment.send(issue, message=message)
        return marshal(issue, issue_fields), 200


@ns.route('/', endpoint='all_issues')
class ListIssuesAPI(API):
    '''
    List all issues.
    '''
    @api.doc(id='list_issues', parser=parser)
    @api.marshal_with(issue_page_fields)
    def get(self):
        '''List all Issues for an object given its ID'''
        args = parser.parse_args()
        issues = Issue.objects
        if not args['closed']:
            issues = issues(closed=None)
        return issues.paginate(args['page'], args['page_size'])
