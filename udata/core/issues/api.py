# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request

from flask.ext.security import current_user

from udata.api import api, API, marshal, fields

from udata.core.user.api import UserField

from .forms import IssueCreateForm, IssueCommentForm
from .models import Issue, Message
from .signals import on_new_issue, on_issue_closed

message_fields = api.model('IssueMessage', {
    'content': fields.String,
    'posted_by': UserField,
    'posted_on': fields.ISODateTime,
})

issue_fields = api.model('Issue', {
    'id': fields.String,
    'type': fields.String,
    'subject': fields.String(attribute='subject.id'),
    'user': UserField,
    'created': fields.ISODateTime,
    'closed': fields.ISODateTime,
    'closed_by': fields.String(attribute='closed_by.id'),
    'discussion': fields.Nested(message_fields),
    'url': fields.UrlFor('api.issue'),
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
        issue.discussion.append(Message(
            content=form.comment.data,
            posted_by=current_user.id
        ))
        close = form.close.data
        if close:
            issue.closed_by = current_user._get_current_object()
            issue.closed = datetime.now()
        issue.save()
        if close:
            on_issue_closed.send(issue)
        return marshal(issue, issue_fields), 200
