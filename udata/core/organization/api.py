# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request, url_for
from werkzeug.datastructures import FileStorage

from udata import search
from udata.api import api, API
from udata.auth import admin_permission, current_user
from udata.core.followers.api import FollowAPI
from udata.utils import multi_to_dict

from .forms import (
    BadgeForm, OrganizationForm, MembershipRequestForm, MembershipRefuseForm,
    MemberForm
)
from .models import (
    OrganizationBadge, Organization, MembershipRequest, Member, FollowOrg,
    ORG_BADGE_KINDS
)
from .permissions import (
    EditOrganizationPermission, OrganizationPrivatePermission
)
from .tasks import notify_membership_request, notify_membership_response
from .search import OrganizationSearch
from .api_fields import (
    badge_fields,
    org_fields,
    org_page_fields,
    org_suggestion_fields,
    request_fields,
    member_fields,
    logo_fields,
)

from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import Dataset
from udata.core.discussions.api import discussion_fields
from udata.core.discussions.models import Discussion
from udata.core.issues.api import issue_fields
from udata.core.issues.models import Issue
from udata.core.reuse.api_fields import reuse_fields
from udata.core.reuse.models import Reuse

ns = api.namespace('organizations', 'Organization related operations')
search_parser = api.search_parser(OrganizationSearch)

common_doc = {
    'params': {'org': 'The organization ID or slug'}
}


@ns.route('/', endpoint='organizations')
class OrganizationListAPI(API):
    '''Organizations collection endpoint'''
    @api.doc('list_organizations', parser=search_parser)
    @api.marshal_with(org_page_fields)
    def get(self):
        '''List or search all organizations'''
        return search.query(OrganizationSearch, **multi_to_dict(request.args))

    @api.secure
    @api.doc('create_organization', responses={400: 'Validation error'})
    @api.expect(org_fields)
    @api.marshal_with(org_fields)
    def post(self):
        '''Create a new organization'''
        form = api.validate(OrganizationForm)
        organization = form.save()
        return organization, 201


@ns.route('/<org:org>/', endpoint='organization', doc=common_doc)
@api.response(404, 'Organization not found')
@api.response(410, 'Organization has been deleted')
class OrganizationAPI(API):
    @api.doc('get_organization')
    @api.marshal_with(org_fields)
    def get(self, org):
        '''Get a organization given its identifier'''
        if org.deleted:
            api.abort(410, 'Organization has been deleted')
        return org

    @api.secure
    @api.doc('update_organization')
    @api.expect(org_fields)
    @api.marshal_with(org_fields)
    @api.response(400, 'Validation error')
    def put(self, org):
        '''Update a organization given its identifier'''
        if org.deleted:
            api.abort(410, 'Organization has been deleted')
        EditOrganizationPermission(org).test()
        form = api.validate(OrganizationForm, org)
        return form.save()

    @api.secure
    @api.doc('delete_organization')
    @api.response(204, 'Organization deleted')
    def delete(self, org):
        '''Delete a organization given its identifier'''
        if org.deleted:
            api.abort(410, 'Organization has been deleted')
        EditOrganizationPermission(org).test()
        org.deleted = datetime.now()
        org.save()
        return '', 204


@ns.route('/badges/', endpoint='available_organization_badges')
class AvailableOrganizationBadgesAPI(API):
    @api.doc('available_organization_badges')
    def get(self):
        '''List all available organization badges and their labels'''
        return ORG_BADGE_KINDS


@ns.route('/<org:org>/badges/', endpoint='organization_badges')
class OrganizationBadgesAPI(API):
    @api.doc('add_organization_badge', **common_doc)
    @api.expect(badge_fields)
    @api.marshal_with(badge_fields)
    @api.secure(admin_permission)
    def post(self, org):
        '''Create a new badge for a given organization'''
        form = api.validate(BadgeForm)
        badge = OrganizationBadge(created=datetime.now(),
                                  created_by=current_user.id)
        form.populate_obj(badge)
        for existing_badge in org.badges:
            if existing_badge.kind == badge.kind:
                return existing_badge
        org.add_badge(badge)
        return badge, 201


@ns.route('/<org:org>/badges/<badge_kind>/', endpoint='organization_badge')
class OrganizationBadgeAPI(API):
    @api.doc('delete_organization_badge', **common_doc)
    @api.secure(admin_permission)
    def delete(self, org, badge_kind):
        '''Delete a badge for a given organization'''
        badge = None
        for badge in org.badges:
            if badge.kind == badge_kind:
                break
        if badge is None:
            api.abort(404, 'Badge does not exists')
        org.remove_badge(badge)
        return '', 204


requests_parser = api.parser()
requests_parser.add_argument(
    'status',
    type=unicode,
    help='If provided, only return requests ith a given status',
    location='args'
)


@ns.route('/<org:org>/membership/', endpoint='request_membership',
          doc=common_doc)
class MembershipRequestAPI(API):
    @api.secure
    @api.marshal_list_with(request_fields)
    @api.doc('list_membership_requests', parser=requests_parser)
    @api.doc(responses={403: 'Not Authorized'})
    def get(self, org):
        '''List membership requests for a given organization'''
        OrganizationPrivatePermission(org).test()
        args = requests_parser.parse_args()
        if args['status']:
            return [r for r in org.requests if r.status == args['status']]
        else:
            return org.requests

    @api.secure
    @api.marshal_with(request_fields)
    def post(self, org):
        '''Apply for membership to a given organization.'''
        membership_request = org.pending_request(
            current_user._get_current_object())
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


@ns.route('/<org:org>/membership/<uuid:id>/accept/',
          endpoint='accept_membership')
class MembershipAcceptAPI(MembershipAPI):
    @api.secure
    @api.doc('accept_membership', **common_doc)
    @api.marshal_with(member_fields)
    def post(self, org, id):
        '''Accept user membership to a given organization.'''
        EditOrganizationPermission(org).test()
        membership_request = self.get_or_404(org, id)

        membership_request.status = 'accepted'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        member = Member(user=membership_request.user, role='editor')

        org.members.append(member)
        org.save()

        notify_membership_response.delay(org, membership_request)

        return member


refuse_parser = api.parser()
refuse_parser.add_argument(
    'comment', type=unicode, help='The refusal reason', location='json'
)


@ns.route('/<org:org>/membership/<uuid:id>/refuse/',
          endpoint='refuse_membership')
class MembershipRefuseAPI(MembershipAPI):
    @api.secure
    @api.doc('refuse_membership', parser=refuse_parser, **common_doc)
    def post(self, org, id):
        '''Refuse user membership to a given organization.'''
        EditOrganizationPermission(org).test()
        membership_request = self.get_or_404(org, id)
        form = api.validate(MembershipRefuseForm)

        membership_request.status = 'refused'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        membership_request.refusal_comment = form.comment.data

        org.save()

        notify_membership_response.delay(org, membership_request)

        return {}, 200


@ns.route('/<org:org>/member/<user:user>', endpoint='member', doc=common_doc)
class MemberAPI(API):
    @api.secure
    @api.expect(member_fields)
    @api.marshal_with(member_fields, code=201)
    @api.doc('create_organization_member')
    @api.response(403, 'Not Authorized')
    @api.response(409, 'User is already member', member_fields)
    def post(self, org, user):
        '''Add a member into a given organization.'''
        EditOrganizationPermission(org).test()
        if org.is_member(user):
            return org.member(user), 409
        member = Member(user=user)
        form = api.validate(MemberForm, member)
        form.populate_obj(member)
        org.members.append(member)
        org.save()

        return member, 201

    @api.secure
    @api.expect(member_fields)
    @api.marshal_with(member_fields)
    @api.doc('update_organization_member', responses={403: 'Not Authorized'})
    def put(self, org, user):
        '''Update member status into a given organization.'''
        EditOrganizationPermission(org).test()
        member = org.member(user)
        form = api.validate(MemberForm, member)
        form.populate_obj(member)
        org.save()

        return member

    @api.secure
    @api.doc('delete_organization_member', responses={403: 'Not Authorized'})
    def delete(self, org, user):
        '''Delete member from an organization'''
        EditOrganizationPermission(org).test()
        member = org.member(user)
        if member:
            Organization.objects(id=org.id).update_one(pull__members=member)
            return '', 204
        else:
            api.abort(404)


@ns.route('/<id>/followers/', endpoint='organization_followers')
class FollowOrgAPI(FollowAPI):
    model = FollowOrg


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=unicode,
    help='The string to autocomplete/suggest', location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


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


logo_parser = api.parser()
logo_parser.add_argument('file', type=FileStorage, location='files')
logo_parser.add_argument('bbox', type=str, location='form')


@ns.route('/<org:org>/logo', endpoint='organization_logo')
@api.doc(parser=logo_parser, **common_doc)
class AvatarAPI(API):
    @api.secure
    @api.doc('organization_logo')
    @api.marshal_with(logo_fields)
    def post(self, org):
        '''Upload a new logo'''
        EditOrganizationPermission(org).test()
        args = logo_parser.parse_args()

        logo = args['file']
        bbox = ([int(float(c)) for c in args['bbox'].split(',')]
                if 'bbox' in args else None)
        org.logo.save(logo, bbox=bbox)
        org.save()

        return org

    @api.secure
    @api.doc('resize_organization_logo')
    @api.marshal_with(logo_fields)
    def put(self, org):
        '''Set the logo BBox'''
        EditOrganizationPermission(org).test()
        args = logo_parser.parse_args()
        logo = args['file']
        org.logo.save(logo, bbox=args.get('bbox'))
        return org


@ns.route('/<org:org>/datasets/', endpoint='org_datasets')
class OrgDatasetsAPI(API):
    @api.doc('list_organization_datasets')
    @api.marshal_list_with(dataset_fields)
    def get(self, org):
        '''List organization datasets (including private ones when member)'''
        qs = Dataset.objects.owned_by(org)
        if not OrganizationPrivatePermission(org).can():
            qs = qs(private__ne=True)
        return list(qs)


@ns.route('/<org:org>/reuses/', endpoint='org_reuses')
class OrgReusesAPI(API):
    @api.doc('list_organization_reuses')
    @api.marshal_list_with(reuse_fields)
    def get(self, org):
        '''List organization reuses (including private ones when member)'''
        qs = Reuse.objects.owned_by(org)
        if not OrganizationPrivatePermission(org).can():
            qs = qs(private__ne=True)
        return list(qs)


@ns.route('/<org:org>/issues/', endpoint='org_issues')
class OrgIssuesAPI(API):
    @api.doc('list_organization_issues')
    @api.marshal_list_with(issue_fields)
    def get(self, org):
        '''List organization issues'''
        reuses_ids = [r.id for r in Reuse.objects(organization=org).only('id')]
        datasets_ids = [d.id
                        for d in Dataset.objects(organization=org).only('id')]
        ids = reuses_ids + datasets_ids
        qs = Issue.objects(subject__in=ids).order_by('-created')
        return list(qs)


@ns.route('/<org:org>/discussions/', endpoint='org_discussions')
class OrgDiscussionsAPI(API):
    @api.doc('list_organization_discussions')
    @api.marshal_list_with(discussion_fields)
    def get(self, org):
        '''List organization discussions'''
        reuses_ids = [r.id for r in Reuse.objects(organization=org).only('id')]
        datasets_ids = [d.id
                        for d in Dataset.objects(organization=org).only('id')]
        ids = reuses_ids + datasets_ids
        qs = Discussion.objects(subject__in=ids).order_by('-created')
        return list(qs)
