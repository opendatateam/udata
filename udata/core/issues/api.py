# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API, fields
from udata.models import Dataset, DatasetIssue, Reuse, ReuseIssue
from udata.core.user.api_fields import user_ref_fields

from .forms import IssueCommentForm, IssueCreateForm
from .models import Message, Issue
from .permissions import CloseIssuePermission
from .signals import on_new_issue, on_new_issue_comment, on_issue_closed

ns = api.namespace('issues', 'Issue related operations')

message_fields = api.model('IssueMessage', {
    'content': fields.String(description='The message body', required=True),
    'posted_by': fields.Nested(
        user_ref_fields, description='The message author', required=True),
    'posted_on': fields.ISODateTime(
        description='The message posting date', required=True),
})

issue_fields = api.model('Issue', {
    'id': fields.String(description='The issue identifier', readonly=True),
    'subject': fields.String(
        attribute='subject.id',
        description='The issue target object identifier', required=True),
    'title': fields.String(description='The issue title', required=True),
    'user': fields.Nested(
        user_ref_fields, description='The issue author', required=True),
    'created': fields.ISODateTime(
        description='The issue creation date', readonly=True),
    'closed': fields.ISODateTime(
        description='The issue closing date', readonly=True),
    'closed_by': fields.String(
        attribute='closed_by.id',
        description='The user who closed the issue', readonly=True),
    'discussion': fields.Nested(message_fields),
    'url': fields.UrlFor(
        'api.issue', description='The issue API URI', readonly=True),
})

comment_issue_fields = api.model('IssueResponse', {
    'comment': fields.String(
        description='The comment to submit', required=True),
    'close': fields.Boolean(
        description='Is this a closing response. Only subject owner can close')
})

issue_page_fields = api.model('IssuePage', fields.pager(issue_fields))

parser = api.parser()
parser.add_argument(
    'closed', type=bool, default=False, location='args',
    help='Filter closed issues')
parser.add_argument(
    'for', type=str, location='args', action='append',
    help='Filter issues for a given subject')
parser.add_argument(
    'page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument(
    'page_size', type=int, default=20, location='args',
    help='The page size to fetch')


@ns.route('/<id>/', endpoint='issue')
@api.doc(model=issue_fields)
class IssueAPI(API):
    '''
    Single Issue Model API (Read and update).
    '''
    @api.doc('get_issue')
    @api.marshal_with(issue_fields)
    def get(self, id):
        '''Get an issue given its ID'''
        issue = Issue.objects.get_or_404(id=id)
        return issue

    @api.secure
    @api.doc('comment_issue')
    @api.expect(comment_issue_fields)
    @api.response(403, 'Not allowed to close this issue')
    @api.marshal_with(issue_fields)
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
            CloseIssuePermission(issue).test()
            issue.closed_by = current_user._get_current_object()
            issue.closed = datetime.now()
        issue.save()
        if close:
            on_issue_closed.send(issue, message=message)
        else:
            on_new_issue_comment.send(issue, message=message)
        return issue


@ns.route('/', endpoint='issues')
class IssuesAPI(API):
    '''
    List all issues.
    '''
    @api.doc('list_issues')
    @api.doc(parser=parser)
    @api.marshal_with(issue_page_fields)
    def get(self):
        '''List all Issues'''
        args = parser.parse_args()
        issues = Issue.objects
        if args['for']:
            issues = issues(subject__in=args['for'])
        if not args['closed']:
            issues = issues(closed=None)
        return issues.paginate(args['page'], args['page_size'])

    @api.secure
    @api.expect(issue_fields)
    @api.doc('create_issue')
    @api.marshal_with(issue_fields)
    def post(self):
        '''Create a new Issue'''
        form = api.validate(IssueCreateForm)

        message = Message(
            content=form.comment.data,
            posted_by=current_user.id
        )
        if isinstance(form.subject.data, Dataset):
            model = DatasetIssue
        elif isinstance(form.subject.data, Reuse):
            model = ReuseIssue
        issue = model.objects.create(
            subject=form.subject.data.id,
            title=form.title.data,
            user=current_user.id,
            discussion=[message]
        )
        on_new_issue.send(issue)

        return issue, 201
