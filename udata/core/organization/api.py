# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request

from udata import search
from udata.api import api, API, errors
from udata.auth import admin_permission, current_user
from udata.core.badges import api as badges_api
from udata.core.followers.api import FollowAPI
from udata.utils import multi_to_dict

from .forms import (
    OrganizationForm, MembershipRequestForm, MembershipRefuseForm, MemberForm
)
from .models import Organization, MembershipRequest, Member
from .permissions import (
    EditOrganizationPermission, OrganizationPrivatePermission
)
from .tasks import notify_membership_request, notify_membership_response
from .search import OrganizationSearch
from .api_fields import (
    org_fields,
    org_page_fields,
    org_suggestion_fields,
    request_fields,
    member_fields,
    refuse_membership_fields,
)

from udata.core.dataset.api_fields import dataset_page_fields
from udata.core.dataset.models import Dataset
from udata.core.dataset.search import DatasetSearch
from udata.core.discussions.api import discussion_fields
from udata.core.discussions.models import Discussion
from udata.core.issues.api import issue_fields
from udata.core.issues.models import Issue
from udata.core.reuse.api_fields import reuse_fields
from udata.core.reuse.models import Reuse
from udata.core.storages.api import (
    uploaded_image_fields, image_parser, parse_uploaded_image
)

ns = api.namespace('organizations', 'Organization related operations')
search_parser = OrganizationSearch.as_request_parser()
dataset_search_parser = DatasetSearch.as_request_parser()

common_doc = {
    'params': {'org': 'The organization ID or slug'}
}


@ns.route('/', endpoint='organizations')
class OrganizationListAPI(API):
    '''Organizations collection endpoint'''
    @api.doc('list_organizations')
    @api.expect(search_parser)
    @api.marshal_with(org_page_fields)
    def get(self):
        '''List or search all organizations'''
        search_parser.parse_args()
        return search.query(OrganizationSearch, **multi_to_dict(request.args))

    @api.secure
    @api.doc('create_organization', responses={400: 'Validation error'})
    @api.expect(org_fields)
    @api.marshal_with(org_fields, code=201)
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
        if org.deleted and not OrganizationPrivatePermission(org).can():
            api.abort(410, 'Organization has been deleted')
        return org

    @api.secure
    @api.doc('update_organization')
    @api.expect(org_fields)
    @api.marshal_with(org_fields)
    @api.response(400, errors.VALIDATION_ERROR)
    @api.response(410, 'Organization has been deleted')
    def put(self, org):
        '''
        Update a organization given its identifier

        :raises PermissionDenied:
        '''
        request_deleted = request.json.get('deleted', True)
        if org.deleted and request_deleted is not None:
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
        return Organization.__badges__


@ns.route('/<org:org>/badges/', endpoint='organization_badges')
class OrganizationBadgesAPI(API):
    @api.doc('add_organization_badge', **common_doc)
    @api.expect(badges_api.badge_fields)
    @api.marshal_with(badges_api.badge_fields)
    @api.secure(admin_permission)
    def post(self, org):
        '''Create a new badge for a given organization'''
        return badges_api.add(org)


@ns.route('/<org:org>/badges/<badge_kind>/', endpoint='organization_badge')
class OrganizationBadgeAPI(API):
    @api.doc('delete_organization_badge', **common_doc)
    @api.secure(admin_permission)
    def delete(self, org, badge_kind):
        '''Delete a badge for a given organization'''
        return badges_api.remove(org, badge_kind)


requests_parser = api.parser()
requests_parser.add_argument(
    'status',
    type=str,
    help='If provided, only return requests ith a given status',
    location='args'
)


@ns.route('/<org:org>/membership/', endpoint='request_membership',
          doc=common_doc)
class MembershipRequestAPI(API):
    @api.secure
    @api.doc('list_membership_requests')
    @api.expect(requests_parser)
    @api.response(403, 'Not Authorized')
    @api.marshal_list_with(request_fields)
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

        if org.is_member(membership_request.user):
            return org.member(membership_request.user), 409

        membership_request.status = 'accepted'
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.now()
        member = Member(user=membership_request.user, role='editor')

        org.members.append(member)
        org.save()

        notify_membership_response.delay(org, membership_request)

        return member


@ns.route('/<org:org>/membership/<uuid:id>/refuse/',
          endpoint='refuse_membership')
class MembershipRefuseAPI(MembershipAPI):
    @api.secure
    @api.expect(refuse_membership_fields)
    @api.doc('refuse_membership', **common_doc)
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
@ns.doc(get={'id': 'list_organization_followers'},
        post={'id': 'follow_organization'},
        delete={'id': 'unfollow_organization'})
class FollowOrgAPI(FollowAPI):
    model = Organization


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', help='The string to autocomplete/suggest', location='args',
    required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_organizations')
class SuggestOrganizationsAPI(API):
    @api.doc('suggest_organizations')
    @api.expect(suggest_parser)
    @api.marshal_list_with(org_suggestion_fields)
    def get(self):
        '''Suggest organizations'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['text'],
                'name': opt['payload']['name'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'acronym': opt['payload']['acronym'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in search.suggest(args['q'], 'org_suggest', args['size'])
        ]


@ns.route('/<org:org>/logo', endpoint='organization_logo')
@api.doc(**common_doc)
class AvatarAPI(API):
    @api.secure
    @api.doc('organization_logo')
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def post(self, org):
        '''Upload a new logo'''
        EditOrganizationPermission(org).test()
        parse_uploaded_image(org.logo)
        org.save()
        return {'image': org.logo}

    @api.secure
    @api.doc('resize_organization_logo')
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def put(self, org):
        '''Set the logo BBox'''
        EditOrganizationPermission(org).test()
        parse_uploaded_image(org.logo)
        return {'image': org.logo}


dataset_parser = api.page_parser()
dataset_parser.add_argument(
    'sort', type=str, default='-created', location='args',
    help='The sorting attribute')


@ns.route('/<org:org>/datasets/', endpoint='org_datasets')
class OrgDatasetsAPI(API):
    sort_mapping = {
        'created': 'created_at',
        'views': 'metrics.views',
        'updated': 'last_modified',
        'reuses': 'metrics.reuses',
        'followers': 'metrics.followers',
    }

    def map_sort(self, sort):
        """Map sort arg from search index attributes to DB attributes"""
        if not sort:
            return
        if sort[0] == '-':
            mapped = self.sort_mapping.get(sort[1:]) or sort[1:]
            return '-{}'.format(mapped)
        else:
            return self.sort_mapping.get(sort) or sort

    @api.doc('list_organization_datasets')
    @api.expect(dataset_parser)
    @api.marshal_with(dataset_page_fields)
    def get(self, org):
        '''List organization datasets (including private ones when member)'''
        args = dataset_parser.parse_args()
        qs = Dataset.objects.owned_by(org)
        if not OrganizationPrivatePermission(org).can():
            qs = qs(private__ne=True)
        return (qs.order_by(self.map_sort(args['sort']))
                .paginate(args['page'], args['page_size']))


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
        reuses = Reuse.objects(organization=org).only('id')
        datasets = Dataset.objects(organization=org).only('id')
        subjects = list(reuses) + list(datasets)
        qs = Issue.objects(subject__in=subjects).order_by('-created')
        return list(qs)


@ns.route('/<org:org>/discussions/', endpoint='org_discussions')
class OrgDiscussionsAPI(API):
    @api.doc('list_organization_discussions')
    @api.marshal_list_with(discussion_fields)
    def get(self, org):
        '''List organization discussions'''
        reuses = Reuse.objects(organization=org).only('id')
        datasets = Dataset.objects(organization=org).only('id')
        subjects = list(reuses) + list(datasets)
        qs = Discussion.objects(subject__in=subjects).order_by('-created')
        return list(qs)
