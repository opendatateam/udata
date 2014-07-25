# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for
from flask.ext.restful import fields

from udata.api import api, ModelAPI, ModelListAPI, API, marshal
from udata.auth import current_user
from udata.forms import OrganizationForm, MembershipRequestForm, MembershipRefuseForm
from udata.models import Organization, MembershipRequest, Member
from udata.search import OrganizationSearch


org_fields = {
    'id': fields.String,
    'name': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'metrics': fields.Raw,
    'uri': fields.UrlFor('api.organization', lambda o: {'slug': o.slug}),
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
            'uri': url_for('api.organization', slug=organization.slug, _external=True),
            'page': url_for('organizations.show', org=organization, _external=True),
        }


class OrganizationListAPI(ModelListAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm
    search_adapter = OrganizationSearch


class OrganizationAPI(ModelAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm


class MembershipRequestAPI(API):
    '''
    Apply for membership to a given organization.
    '''
    @api.secure
    def post(self, org):
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


class MembershipAcceptAPI(MembershipAPI):
    '''
    Accept user membership to a given organization.
    '''
    @api.secure
    def post(self, org, id):
        membership_request = self.get_or_404(org, id)

        membership_request.status = 'accepted'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        member = Member(user=membership_request.user, role='editor')

        org.members.append(member)
        org.save()

        return marshal(member, member_fields), 200


class MembershipRefuseAPI(MembershipAPI):
    '''
    Refuse user membership to a given organization.
    '''
    @api.secure
    def post(self, org, id):
        membership_request = self.get_or_404(org, id)
        form = api.validate(MembershipRefuseForm)

        membership_request.status = 'refused'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        membership_request.refusal_comment = form.comment.data

        org.save()

        return {}, 200


api.add_resource(OrganizationListAPI, '/organizations/', endpoint=b'api.organizations')
api.add_resource(OrganizationAPI, '/organizations/<slug>', endpoint=b'api.organization')

api.add_resource(MembershipRequestAPI, '/organizations/<org:org>/membership', endpoint=b'api.request_membership')
api.add_resource(MembershipAcceptAPI, '/organizations/<org:org>/membership/<uuid:id>/accept', endpoint=b'api.accept_membership')
api.add_resource(MembershipRefuseAPI, '/organizations/<org:org>/membership/<uuid:id>/refuse', endpoint=b'api.refuse_membership')
