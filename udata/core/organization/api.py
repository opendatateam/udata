# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from werkzeug.datastructures import FileStorage

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, API
from udata.auth import current_user
from udata.forms import OrganizationForm, MembershipRequestForm, MembershipRefuseForm
from udata.models import Organization, MembershipRequest, Member, FollowOrg
from udata.core.followers.api import FollowAPI

from .permissions import EditOrganizationPermission, OrganizationPrivatePermission
from .tasks import notify_membership_request, notify_membership_response
from .search import OrganizationSearch
from .api_fields import (
    org_fields,
    org_page_fields,
    org_suggestion_fields,
    request_fields,
    member_fields,
    logo_fields,
)

ns = api.namespace('organizations', 'Organization related operations')
search_parser = api.search_parser(OrganizationSearch)

common_doc = {
    'params': {'org': 'The organization ID or slug'}
}


@ns.route('/', endpoint='organizations')
@api.doc(get={'id': 'list_organizations', 'model': org_page_fields, 'parser': search_parser})
@api.doc(post={'id': 'create_organization', 'model': org_fields, 'body': org_fields})
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


requests_parser = api.parser()
requests_parser.add_argument('status', type=unicode,
    help='If provided, only return requests ith a given status', location='args'
)


@ns.route('/<org:org>/membership/', endpoint='request_membership', doc=common_doc)
class MembershipRequestAPI(API):
    @api.secure
    @api.marshal_list_with(request_fields)
    @api.doc('list_membership_requests', parser=requests_parser)
    @api.doc(responses={403: 'Not Authorized'})
    def get(self, org):
        '''List membership requests for a given organization'''
        OrganizationPrivatePermission(org.id).test()
        args = requests_parser.parse_args()
        if args['status']:
            return [r for r in org.requests if r.status == args['status']]
        else:
            return org.requests

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


@ns.route('/<org:org>/membership/<uuid:id>/accept/', endpoint='accept_membership')
class MembershipAcceptAPI(MembershipAPI):
    @api.secure
    @api.doc('accept_membership', **common_doc)
    @api.marshal_with(member_fields)
    def post(self, org, id):
        '''Accept user membership to a given organization.'''
        EditOrganizationPermission(org.id).test()
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
refuse_parser.add_argument('comment', type=unicode,
    help='The refusal reason', location='json'
)


@ns.route('/<org:org>/membership/<uuid:id>/refuse/', endpoint='refuse_membership')
class MembershipRefuseAPI(MembershipAPI):
    @api.secure
    @api.doc('refuse_membership', parser=refuse_parser, **common_doc)
    def post(self, org, id):
        '''Refuse user membership to a given organization.'''
        EditOrganizationPermission(org.id).test()
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
        args = logo_parser.parse_args()

        logo = args['file']
        bbox = [int(float(c)) for c in args['bbox'].split(',')] if 'bbox' in args else None
        org.logo.save(logo, bbox=bbox)
        org.save()

        return org

    @api.secure
    @api.doc('resize_organization_logo')
    @api.marshal_with(logo_fields)
    def put(self, org):
        '''Set the logo BBox'''
        args = logo_parser.parse_args()

        print args
        logo = args['file']

        org.logo.save(logo, bbox=args.get('bbox'))

        return org

        # storage = storages.logo

        # prefix = self.get_prefix(dataset)

        # filename = storage.save(file, prefix=prefix)

        # extension = fileutils.extension(filename)

        # file.seek(0)
        # sha1 = storages.utils.sha1(file)

        # size = os.path.getsize(storage.path(filename)) if storage.root else None

        # resource = Resource(
        #     title=os.path.basename(filename),
        #     url=storage.url(filename, external=True),
        #     checksum=Checksum(value=sha1),
        #     format=extension,
        #     mime=storages.utils.mime(filename),
        #     size=size
        # )
        # dataset.add_resource(resource)
        # return resource, 201
