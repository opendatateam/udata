# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for
from flask.ext.restful import fields

from udata.api import api, ModelAPI, ModelListAPI, API, marshal
from udata.auth import current_user
from udata.forms import OrganizationForm, MembershipRequestForm, MembershipRefuseForm
from udata.models import Organization, MembershipRequest, Member

from .search import OrganizationSearch

ns = api.namespace('organizations', 'Organization related operations')

org_fields = {
    'id': fields.String,
    'name': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime,
    'deleted': fields.ISODateTime,
    'metrics': fields.Raw,
    'uri': fields.UrlFor('api.organization', lambda o: {'org': o}),
}

request_fields = {
    'status': fields.String,
    'comment': fields.String,
}

member_fields = {
    'user': fields.String,
    'role': fields.String,
}


class OrganizationField(fields.Raw):
    def format(self, organization):
        return {
            'id': str(organization.id),
            'uri': url_for('api.organization', org=organization, _external=True),
            'page': url_for('organizations.show', org=organization, _external=True),
        }


@ns.route('/', endpoint='organizations')
class OrganizationListAPI(ModelListAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm
    search_adapter = OrganizationSearch


@ns.route('/<org:org>/', endpoint='organization')
class OrganizationAPI(ModelAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm


@ns.route('/<org:org>/membership/', endpoint='request_membership')
class MembershipRequestAPI(API):
    @api.secure
    def post(self, org):
        '''Apply for membership to a given organization.'''
        membership_request = org.pending_request(current_user._get_current_object())
        code = 200 if membership_request else 201

        form = api.validate(MembershipRequestForm, membership_request)

        if not membership_request:
            membership_request = MembershipRequest()
            org.requests.append(membership_request)

        form.populate_obj(membership_request)
        org.save()

        return marshal(membership_request, request_fields), code


class MembershipAPI(API):
    def get_or_404(self, org, id):
        for membership_request in org.requests:
            if membership_request.id == id:
                return membership_request
        api.abort(404, 'Unknown membership request id')


@ns.route('/<org:org>/membership/<uuid:id>/accept/', endpoint='accept_membership')
class MembershipAcceptAPI(MembershipAPI):
    @api.secure
    def post(self, org, id):
        '''Accept user membership to a given organization.'''
        membership_request = self.get_or_404(org, id)

        membership_request.status = 'accepted'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        member = Member(user=membership_request.user, role='editor')

        org.members.append(member)
        org.save()

        return marshal(member, member_fields), 200


@ns.route('/<org:org>/membership/<uuid:id>/refuse/', endpoint='refuse_membership')
class MembershipRefuseAPI(MembershipAPI):
    @api.secure
    def post(self, org, id):
        '''Refuse user membership to a given organization.'''
        membership_request = self.get_or_404(org, id)
        form = api.validate(MembershipRefuseForm)

        membership_request.status = 'refused'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        membership_request.refusal_comment = form.comment.data

        org.save()

        return {}, 200
