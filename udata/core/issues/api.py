# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import abort, request

from flask.ext.security import current_user

from udata.api import api, API, marshal, fields

from udata.core.user.api import UserField

from .models import Issue, Message
from .signals import on_new_issue, on_issue_closed

message_fields = {
    'content': fields.String,
    'posted_by': UserField,
    'posted_on': fields.ISODateTime,
}

issue_fields = {
    'id': fields.String,
    'type': fields.String,
    'subject': fields.String(attribute='subject.id'),
    'user': UserField,
    'created': fields.ISODateTime,
    'closed': fields.ISODateTime,
    'closed_by': fields.String(attribute='closed_by.id'),
    'discussion': fields.Nested(message_fields),
    'url': fields.SelfUrl('api.issue'),
}


class IssuesAPI(API):
    '''
    Base Issues Model API (Create and list).
    '''
    model = Issue

    def post(self, id):
        if not current_user.is_authenticated():
            abort(401)
        message = Message(content=request.form['comment'], posted_by=current_user.id)
        issue = self.model.objects.create(
            subject=id,
            type=request.form['type'],
            user=current_user.id,
            discussion=[message]
        )
        on_new_issue.send(issue)

        return marshal(issue, issue_fields), 201

    def get(self, id):
        issues = self.model.objects(subject=id)
        if not request.args.get('closed'):
            issues = issues(closed=None)
        return marshal(list(issues), issue_fields)


class IssueAPI(API):
    '''
    Single Issue Model API (Read and update).
    '''

    def get(self, id):
        issue = Issue.objects.get_or_404(id=id)
        return marshal(issue, issue_fields)

    def post(self, id):
        if not current_user.is_authenticated():
            abort(401)
        issue = Issue.objects.get_or_404(id=id)
        issue.discussion.append(Message(
            content=request.form['comment'],
            posted_by=current_user.id
        ))
        close = request.form.get('close', '').lower() == 'true'
        if close:
            issue.closed_by = current_user._get_current_object()
            issue.closed = datetime.now()
        issue.save()
        if close:
            on_issue_closed.send(issue)
        return marshal(issue, issue_fields), 200


api.add_resource(IssueAPI, '/issues/<id>', endpoint=b'api.issue')
