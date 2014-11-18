# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request

from flask.ext.security import current_user

from udata.api import api, API, marshal, fields

from udata.core.user.api_fields import UserReference

from .forms import IssueCreateForm, IssueCommentForm
from .models import Issue, Message, ISSUE_TYPES
from .signals import on_new_issue, on_new_issue_comment, on_issue_closed

message_fields = api.model('IssueMessage', {
    'content': fields.String(description='The message body', required=True),
    'posted_by': UserReference(description='The message author', required=True),
    'posted_on': fields.ISODateTime(description='The message posting date', required=True),
})

issue_fields = api.model('Issue', {
    'id': fields.String(description='The issue identifier', required=True),
    'type': fields.String(description='The issue type', required=True, enum=ISSUE_TYPES.keys()),
    'subject': fields.String(attribute='subject.id', description='The issue target object identifier', required=True),
    'user': UserReference(description='The issue author', required=True),
    'created': fields.ISODateTime(description='The issue creation date', required=True),
    'closed': fields.ISODateTime(description='The issue closing date'),
    'closed_by': fields.String(attribute='closed_by.id', description='The user who closed the issue'),
    'discussion': fields.Nested(message_fields),
    'url': fields.UrlFor('api.issue', description='The issue API URI', required=True),
})


class IssuesAPI(API):
    '''
    Base Issues Model API (Create and list).
    '''
    model = Issue

    @api.secure
    @api.doc(model=issue_fields)
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

    @api.doc(model=[issue_fields])
    def get(self, id):
        '''List all Issues for an object given its ID'''
        issues = self.model.objects(subject=id)
        if not request.args.get('closed'):
            issues = issues(closed=None)
        return marshal(list(issues), issue_fields)


@api.route('/issues/<id>', endpoint='issue')
@api.doc(model=issue_fields)
class IssueAPI(API):
    '''
    Single Issue Model API (Read and update).
    '''

    def get(self, id):
        '''Get an issue given its ID'''
        issue = Issue.objects.get_or_404(id=id)
        return marshal(issue, issue_fields)

    @api.secure
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
