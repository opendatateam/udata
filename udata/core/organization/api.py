# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, API, marshal
from udata.auth import current_user
from udata.forms import OrganizationForm, MembershipRequestForm, MembershipRefuseForm
from udata.models import Organization, MembershipRequest, Member, FollowOrg

from udata.core.followers.api import FollowAPI

from .tasks import notify_membership_request, notify_membership_response
from .search import OrganizationSearch
from .api_fields import org_fields, org_page_fields, org_suggestion_fields, request_fields, member_fields

ns = api.namespace('organizations', 'Organization related operations')
search_parser = api.search_parser(OrganizationSearch)

common_doc = {
    'params': {'org': 'The organization ID or slug'}
}


@ns.route('/', endpoint='organizations')
@api.doc(get={'id': 'list_organizations', 'model': org_page_fields, 'parser': search_parser})
@api.doc(post={'id': 'create_organization', 'model': org_fields})
class OrganizationListAPI(ModelListAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm
    search_adapter = OrganizationSearch


@ns.route('/<org:org>/', endpoint='organization', doc=common_doc)
@api.doc(model=org_fields, get={'id': 'get_organization'})
@api.doc(put={'id': 'update_organization', 'body': org_fields})
class OrganizationAPI(ModelAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm


@ns.route('/<org:org>/membership/', endpoint='request_membership', doc=common_doc)
class MembershipRequestAPI(API):
    @api.secure
    @api.marshal_with(request_fields)
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

        notify_membership_request.delay(org, membership_request)

        return membership_request, code


class MembershipAPI(API):
    def get_or_404(self, org, id):
        for membership_request in org.requests:
            if membership_request.id == id:
                return membership_request
        api.abort(404, 'Unknown membership request id')


@ns.route('/<org:org>/membership/<uuid:id>/accept/', endpoint='accept_membership', doc=common_doc)
class MembershipAcceptAPI(MembershipAPI):
    @api.secure
    @api.marshal_with(member_fields)
    def post(self, org, id):
        '''Accept user membership to a given organization.'''
        membership_request = self.get_or_404(org, id)

        membership_request.status = 'accepted'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        member = Member(user=membership_request.user, role='editor')

        org.members.append(member)
        org.save()

        notify_membership_response.delay(org, membership_request)

        return member


@ns.route('/<org:org>/membership/<uuid:id>/refuse/', endpoint='refuse_membership', doc=common_doc)
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

        notify_membership_response.delay(org, membership_request)

        return {}, 200


@ns.route('/<id>/followers/', endpoint='organization_followers')
class FollowOrgAPI(FollowAPI):
    model = FollowOrg


suggest_parser = api.parser()
suggest_parser.add_argument('q', type=unicode, help='The string to autocomplete/suggest', location='args', required=True)
suggest_parser.add_argument('size', type=int, help='The amount of suggestion to fetch', location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_organizations')
class SuggestOrganizationsAPI(API):
    @api.marshal_list_with(org_suggestion_fields)
    @api.doc(id='suggest_organizations', parser=suggest_parser)
    def get(self):
        '''Suggest organizations'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['payload']['id'],
                'name': opt['text'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in search.suggest(args['q'], 'org_suggest', args['size'])
        ]
