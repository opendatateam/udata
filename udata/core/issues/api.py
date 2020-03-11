from datetime import datetime

from flask_security import current_user
from flask_restplus.inputs import boolean

from udata.api import api, API, fields
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
    'subject': fields.Nested(api.model_reference,
                             description='The issue target object',
                             required=True),
    'class': fields.ClassName(description='The object class',
                              discriminator=True, required=True),
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
    'sort', type=str, default='-created', location='args',
    help='The sorting attribute')
parser.add_argument(
    'closed', type=boolean, location='args',
    help='Filter closed issues. Filters issues on their closed status'
    ' if specified')
parser.add_argument(
    'for', type=str, location='args', action='append',
    help='Filter issues for a given subject')
parser.add_argument(
    'page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument(
    'page_size', type=int, default=20, location='args',
    help='The page size to fetch')


@ns.route('/<id>/', endpoint='issue')
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
        '''Add comment and optionally close an issue given its ID'''
        issue = Issue.objects.get_or_404(id=id)
        form = api.validate(IssueCommentForm)
        message = Message(
            content=form.comment.data,
            posted_by=current_user.id
        )
        issue.discussion.append(message)
        message_idx = len(issue.discussion) - 1
        close = form.close.data
        if close:
            CloseIssuePermission(issue).test()
            issue.closed_by = current_user._get_current_object()
            issue.closed = datetime.now()
        issue.save()
        if close:
            on_issue_closed.send(issue, message=message_idx)
        else:
            on_new_issue_comment.send(issue, message=message_idx)
        return issue


@ns.route('/', endpoint='issues')
class IssuesAPI(API):
    '''
    List all issues.
    '''
    @api.doc('list_issues')
    @api.expect(parser)
    @api.marshal_with(issue_page_fields)
    def get(self):
        '''List all Issues'''
        args = parser.parse_args()
        issues = Issue.objects
        if args['for']:
            issues = issues.generic_in(subject=args['for'])
        if args['closed'] is False:
            issues = issues(closed=None)
        elif args['closed'] is True:
            issues = issues(closed__ne=None)
        issues = issues.order_by(args['sort'])
        return issues.paginate(args['page'], args['page_size'])

    @api.secure
    @api.doc('create_issue')
    @api.expect(issue_fields)
    @api.marshal_with(issue_fields)
    def post(self):
        '''Create a new Issue'''
        form = api.validate(IssueCreateForm)

        message = Message(
            content=form.comment.data,
            posted_by=current_user.id
        )
        issue = Issue(user=current_user.id, discussion=[message])
        form.populate_obj(issue)
        issue.save()
        on_new_issue.send(issue)

        return issue, 201
