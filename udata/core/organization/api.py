import itertools
from datetime import datetime

from flask import make_response, redirect, request, url_for
from mongoengine.queryset.visitor import Q

from udata.api import API, api, errors
from udata.api.parsers import ModelApiParser
from udata.auth import admin_permission, current_user
from udata.core import csv
from udata.core.badges import api as badges_api
from udata.core.badges.fields import badge_fields
from udata.core.contact_point.api import ContactPointApiParser
from udata.core.contact_point.api_fields import contact_point_fields, contact_point_page_fields
from udata.core.dataservices.csv import DataserviceCsvAdapter
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api import DatasetApiParser
from udata.core.dataset.api_fields import dataset_page_fields
from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter
from udata.core.dataset.models import Dataset
from udata.core.discussions.api import discussion_fields
from udata.core.discussions.csv import DiscussionCsvAdapter
from udata.core.discussions.models import Discussion
from udata.core.followers.api import FollowAPI
from udata.core.reuse.models import Reuse
from udata.core.storages.api import (
    image_parser,
    parse_uploaded_image,
    uploaded_image_fields,
)
from udata.models import ContactPoint
from udata.rdf import RDF_EXTENSIONS, graph_response, negociate_content
from udata.utils import multi_to_dict

from .api_fields import (
    member_fields,
    org_fields,
    org_page_fields,
    org_role_fields,
    org_suggestion_fields,
    refuse_membership_fields,
    request_fields,
)
from .constants import ORG_ROLES
from .forms import (
    MemberForm,
    MembershipRefuseForm,
    MembershipRequestForm,
    OrganizationForm,
)
from .models import Member, MembershipRequest, Organization
from .permissions import EditOrganizationPermission, OrganizationPrivatePermission
from .rdf import build_org_catalog
from .tasks import notify_membership_request, notify_membership_response

DEFAULT_SORTING = "-created_at"
SUGGEST_SORTING = "-metrics.followers"


class OrgApiParser(ModelApiParser):
    sorts = {
        "name": "name",
        "reuses": "metrics.reuses",
        "datasets": "metrics.datasets",
        "followers": "metrics.followers",
        "views": "metrics.views",
        "created": "created_at",
        "last_modified": "last_modified",
    }

    def __init__(self):
        super().__init__()
        self.parser.add_argument(
            "badge",
            type=str,
            choices=list(Organization.__badges__),
            location="args",
        )
        self.parser.add_argument(
            "name",
            type=str,
            location="args",
        )
        self.parser.add_argument(
            "business_number_id",
            type=str,
            location="args",
        )

    @staticmethod
    def parse_filters(organizations, args):
        if args.get("q"):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            organizations = organizations.search_text(phrase_query)
        if args.get("badge"):
            organizations = organizations.with_badge(args["badge"])
        if args.get("name"):
            organizations = organizations.filter(name=args["name"])
        if args.get("business_number_id"):
            organizations = organizations.filter(business_number_id=args["business_number_id"])
        return organizations


ns = api.namespace("organizations", "Organization related operations")

organization_parser = OrgApiParser()

common_doc = {"params": {"org": "The organization ID or slug"}}


@ns.route("/", endpoint="organizations")
class OrganizationListAPI(API):
    """Organizations collection endpoint"""

    @api.doc("list_organizations")
    @api.expect(organization_parser.parser)
    @api.marshal_with(org_page_fields)
    def get(self):
        """List or search all organizations"""
        args = organization_parser.parse()
        organizations = Organization.objects(deleted=None)
        organizations = organization_parser.parse_filters(organizations, args)

        sort = args["sort"] or ("$text_score" if args["q"] else None) or DEFAULT_SORTING
        return organizations.order_by(sort).paginate(args["page"], args["page_size"])

    @api.secure
    @api.doc("create_organization", responses={400: "Validation error"})
    @api.expect(org_fields)
    @api.marshal_with(org_fields, code=201)
    def post(self):
        """Create a new organization"""
        form = api.validate(OrganizationForm)
        organization = form.save()
        return organization, 201


@ns.route("/<org:org>/", endpoint="organization", doc=common_doc)
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class OrganizationAPI(API):
    @api.doc("get_organization")
    @api.marshal_with(org_fields)
    def get(self, org):
        """Get a organization given its identifier"""
        if org.deleted and not OrganizationPrivatePermission(org).can():
            api.abort(410, "Organization has been deleted")
        return org

    @api.secure
    @api.doc("update_organization")
    @api.expect(org_fields)
    @api.marshal_with(org_fields)
    @api.response(400, errors.VALIDATION_ERROR)
    @api.response(410, "Organization has been deleted")
    def put(self, org):
        """
        Update a organization given its identifier

        :raises PermissionDenied:
        """
        request_deleted = request.json.get("deleted", True)
        if org.deleted and request_deleted is not None:
            api.abort(410, "Organization has been deleted")
        EditOrganizationPermission(org).test()
        form = api.validate(OrganizationForm, org)
        return form.save()

    @api.secure
    @api.doc("delete_organization")
    @api.response(204, "Organization deleted")
    def delete(self, org):
        """Delete a organization given its identifier"""
        if org.deleted:
            api.abort(410, "Organization has been deleted")
        EditOrganizationPermission(org).test()
        org.deleted = datetime.utcnow()
        org.save()
        return "", 204


@ns.route("/<org:org>/datasets.csv", endpoint="organization_datasets_csv", doc=common_doc)
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class DatasetsCsvAPI(API):
    def get(self, org):
        datasets = Dataset.objects(organization=str(org.id)).visible()
        adapter = DatasetCsvAdapter(datasets)
        return csv.stream(adapter, "{0}-datasets".format(org.slug))


@ns.route("/<org:org>/dataservices.csv", endpoint="organization_dataservices_csv")
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class DataservicesCsv(API):
    def get(self, org):
        dataservices = Dataservice.objects(organization=str(org.id)).visible()
        adapter = DataserviceCsvAdapter(dataservices)
        return csv.stream(adapter, "{0}-dataservices".format(org.slug))


@ns.route("/<org:org>/discussions.csv", endpoint="organization_discussions_csv", doc=common_doc)
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class DiscussionsCsvAPI(API):
    def get(self, org):
        datasets = Dataset.objects.filter(organization=str(org.id))
        discussions = [Discussion.objects.filter(subject=dataset) for dataset in datasets]
        # Turns a list of lists into a flat list.
        adapter = DiscussionCsvAdapter(itertools.chain(*discussions))
        return csv.stream(adapter, "{0}-discussions".format(org.slug))


@ns.route(
    "/<org:org>/datasets-resources.csv",
    endpoint="organization_datasets_resources_csv",
    doc=common_doc,
)
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class DatasetsResourcesCsvAPI(API):
    def get(self, org):
        datasets = Dataset.objects(organization=str(org.id)).visible()
        adapter = ResourcesCsvAdapter(datasets)
        return csv.stream(adapter, "{0}-datasets-resources".format(org.slug))


@ns.route("/<org:org>/catalog", endpoint="organization_rdf", doc=common_doc)
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class OrganizationRdfAPI(API):
    @api.doc("rdf_organization")
    def get(self, org):
        format = RDF_EXTENSIONS[negociate_content()]
        url = url_for("api.organization_rdf_format", org=org.id, format=format)
        return redirect(url)


@ns.route("/<org:org>/catalog.<format>", endpoint="organization_rdf_format", doc=common_doc)
@api.response(404, "Organization not found")
@api.response(410, "Organization has been deleted")
class OrganizationRdfFormatAPI(API):
    @api.doc("rdf_organization_format")
    def get(self, org, format):
        if org.deleted:
            api.abort(410)
        params = multi_to_dict(request.args)
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 100))
        datasets = Dataset.objects(organization=org).visible().paginate(page, page_size)
        dataservices = (
            Dataservice.objects(organization=org)
            .visible()
            .filter_by_dataset_pagination(datasets, page)
        )
        catalog = build_org_catalog(org, datasets, dataservices, format=format)
        # bypass flask-restplus make_response, since graph_response
        # is handling the content negociation directly
        return make_response(*graph_response(catalog, format))


@ns.route("/badges/", endpoint="available_organization_badges")
class AvailableOrganizationBadgesAPI(API):
    @api.doc("available_organization_badges")
    def get(self):
        """List all available organization badges and their labels"""
        return Organization.__badges__


@ns.route("/<org:org>/badges/", endpoint="organization_badges")
class OrganizationBadgesAPI(API):
    @api.doc("add_organization_badge", **common_doc)
    @api.expect(badge_fields)
    @api.marshal_with(badge_fields)
    @api.secure(admin_permission)
    def post(self, org):
        """Create a new badge for a given organization"""
        return badges_api.add(org)


@ns.route("/<org:org>/badges/<badge_kind>/", endpoint="organization_badge")
class OrganizationBadgeAPI(API):
    @api.doc("delete_organization_badge", **common_doc)
    @api.secure(admin_permission)
    def delete(self, org, badge_kind):
        """Delete a badge for a given organization"""
        return badges_api.remove(org, badge_kind)


contact_point_parser = ContactPointApiParser()


@ns.route("/<org:org>/contacts/", endpoint="org_contact_points")
class OrgContactAPI(API):
    @api.doc("get_organization_contact_point")
    @api.marshal_with(contact_point_page_fields)
    def get(self, org):
        """List all organization contact points"""
        args = contact_point_parser.parse()
        contact_points = ContactPoint.objects.owned_by(org)
        return contact_points.paginate(args["page"], args["page_size"])


suggest_parser = api.parser()
suggest_parser.add_argument(
    "q", help="The string to autocomplete/suggest", location="args", required=True
)
suggest_parser.add_argument(
    "size", type=int, help="The amount of suggestion to fetch", location="args", default=10
)


@ns.route("/<org:org>/contacts/suggest/", endpoint="suggest_org_contact_points")
class ContactPointSuggestAPI(API):
    @api.doc("suggest_org_contact_points")
    @api.expect(suggest_parser)
    @api.marshal_list_with(contact_point_fields)
    def get(self, org):
        """Contact points suggest endpoint using mongoDB contains"""
        args = suggest_parser.parse_args()
        contact_points = ContactPoint.objects(
            Q(name__icontains=args["q"])
            | Q(email__icontains=args["q"])
            | Q(contact_form__icontains=args["q"])
        ).owned_by(org)
        return list(contact_points.limit(args["size"]))


requests_parser = api.parser()
requests_parser.add_argument(
    "status", type=str, help="If provided, only return requests in a given status", location="args"
)
requests_parser.add_argument(
    "user", type=str, help="If provided, only return requests for this user", location="args"
)


@ns.route("/<org:org>/membership/", endpoint="request_membership", doc=common_doc)
class MembershipRequestAPI(API):
    @api.secure
    @api.doc("list_membership_requests")
    @api.expect(requests_parser)
    @api.response(403, "Not Authorized")
    @api.marshal_list_with(request_fields)
    def get(self, org):
        """List membership requests for a given organization"""
        args = requests_parser.parse_args()
        if args["user"]:
            if not current_user.is_authenticated or (
                str(current_user.id) != args["user"]
                and not OrganizationPrivatePermission(org).can()
            ):
                api.abort(
                    403,
                    "You can only access your own membership requests or the one of your organizations.",
                )
            if args["status"]:
                return [
                    r
                    for r in org.requests
                    if (r.status == args["status"] and str(r.user.id) == args["user"])
                ]
            return [r for r in org.requests if str(r.user.id) == args["user"]]
        OrganizationPrivatePermission(org).test()
        if args["status"]:
            return [r for r in org.requests if r.status == args["status"]]
        else:
            return org.requests

    @api.secure
    @api.marshal_with(request_fields)
    def post(self, org):
        """Apply for membership to a given organization."""
        membership_request = org.pending_request(current_user._get_current_object())
        code = 200 if membership_request else 201

        form = api.validate(MembershipRequestForm, membership_request)

        if not membership_request:
            membership_request = MembershipRequest()
            org.requests.append(membership_request)

        form.populate_obj(membership_request)
        org.save()

        notify_membership_request.delay(str(org.id), str(membership_request.id))

        return membership_request, code


class MembershipAPI(API):
    def get_or_404(self, org, id):
        for membership_request in org.requests:
            if membership_request.id == id:
                return membership_request
        api.abort(404, "Unknown membership request id")


@ns.route("/<org:org>/membership/<uuid:id>/accept/", endpoint="accept_membership")
class MembershipAcceptAPI(MembershipAPI):
    @api.secure
    @api.doc("accept_membership", **common_doc)
    @api.marshal_with(member_fields)
    def post(self, org, id):
        """Accept user membership to a given organization."""
        EditOrganizationPermission(org).test()
        membership_request = self.get_or_404(org, id)

        if org.is_member(membership_request.user):
            return org.member(membership_request.user), 409

        membership_request.status = "accepted"
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.utcnow()
        member = Member(user=membership_request.user, role="editor")

        org.members.append(member)
        org.count_members()
        org.save()

        notify_membership_response.delay(str(org.id), str(membership_request.id))

        return member


@ns.route("/<org:org>/membership/<uuid:id>/refuse/", endpoint="refuse_membership")
class MembershipRefuseAPI(MembershipAPI):
    @api.secure
    @api.expect(refuse_membership_fields)
    @api.doc("refuse_membership", **common_doc)
    def post(self, org, id):
        """Refuse user membership to a given organization."""
        EditOrganizationPermission(org).test()
        membership_request = self.get_or_404(org, id)
        form = api.validate(MembershipRefuseForm)
        membership_request.status = "refused"
        membership_request.handled_by = current_user._get_current_object()
        membership_request.handled_on = datetime.utcnow()
        membership_request.refusal_comment = form.comment.data

        org.save()

        notify_membership_response.delay(str(org.id), str(membership_request.id))

        return {}, 200


@ns.route("/<org:org>/member/<user:user>", endpoint="member", doc=common_doc)
class MemberAPI(API):
    @api.secure
    @api.expect(member_fields)
    @api.marshal_with(member_fields, code=201)
    @api.doc("create_organization_member")
    @api.response(403, "Not Authorized")
    @api.response(409, "User is already member", member_fields)
    def post(self, org, user):
        """Add a member into a given organization."""
        EditOrganizationPermission(org).test()
        if org.is_member(user):
            return org.member(user), 409
        member = Member(user=user)
        form = api.validate(MemberForm, member)
        form.populate_obj(member)
        org.members.append(member)
        org.count_members()
        org.save()

        return member, 201

    @api.secure
    @api.expect(member_fields)
    @api.marshal_with(member_fields)
    @api.doc("update_organization_member", responses={403: "Not Authorized"})
    def put(self, org, user):
        """Update member status into a given organization."""
        EditOrganizationPermission(org).test()
        member = org.member(user)
        form = api.validate(MemberForm, member)
        form.populate_obj(member)
        org.save()

        return member

    @api.secure
    @api.doc("delete_organization_member", responses={403: "Not Authorized"})
    def delete(self, org, user):
        """Delete member from an organization"""
        EditOrganizationPermission(org).test()
        member = org.member(user)
        if member:
            Organization.objects(id=org.id).update_one(pull__members=member)
            org.reload()
            org.count_members()
            return "", 204
        else:
            api.abort(404)


@ns.route("/<id>/followers/", endpoint="organization_followers")
@ns.doc(
    get={"id": "list_organization_followers"},
    post={"id": "follow_organization"},
    delete={"id": "unfollow_organization"},
)
class FollowOrgAPI(FollowAPI):
    model = Organization


@ns.route("/suggest/", endpoint="suggest_organizations")
class OrganizationSuggestAPI(API):
    @api.doc("suggest_organizations")
    @api.expect(suggest_parser)
    @api.marshal_list_with(org_suggestion_fields)
    def get(self):
        """Organizations suggest endpoint using mongoDB contains"""
        args = suggest_parser.parse_args()
        orgs = Organization.objects(
            Q(name__icontains=args["q"]) | Q(acronym__icontains=args["q"]), deleted=None
        )
        return [
            {
                "id": org.id,
                "name": org.name,
                "acronym": org.acronym,
                "slug": org.slug,
                "image_url": org.logo,
                "page": org.self_web_url(),
            }
            for org in orgs.order_by(SUGGEST_SORTING).limit(args["size"])
        ]


@ns.route("/<org:org>/logo/", endpoint="organization_logo")
@api.doc(**common_doc)
class AvatarAPI(API):
    @api.secure
    @api.doc("organization_logo")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def post(self, org):
        """Upload a new logo"""
        EditOrganizationPermission(org).test()
        parse_uploaded_image(org.logo)
        org.save()
        return {"image": org.logo}

    @api.secure
    @api.doc("resize_organization_logo")
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
    @api.marshal_with(uploaded_image_fields)
    def put(self, org):
        """Set the logo BBox"""
        EditOrganizationPermission(org).test()
        parse_uploaded_image(org.logo)
        return {"image": org.logo}


dataset_parser = DatasetApiParser()


@ns.route("/<org:org>/datasets/", endpoint="org_datasets")
class OrgDatasetsAPI(API):
    @api.doc("list_organization_datasets")
    @api.expect(dataset_parser.parser)
    @api.marshal_with(dataset_page_fields)
    def get(self, org):
        """List organization datasets (including private ones when member)"""
        args = dataset_parser.parse()
        qs = Dataset.objects.owned_by(org)
        if not OrganizationPrivatePermission(org).can():
            qs = qs(private__ne=True)
        return qs.order_by(args["sort"]).paginate(args["page"], args["page_size"])


@ns.route("/<org:org>/reuses/", endpoint="org_reuses")
class OrgReusesAPI(API):
    @api.doc("list_organization_reuses")
    @api.marshal_list_with(Reuse.__read_fields__)
    def get(self, org):
        """List organization reuses (including private ones when member)"""
        qs = Reuse.objects.owned_by(org)
        if not OrganizationPrivatePermission(org).can():
            qs = qs(private__ne=True)
        return list(qs)


@ns.route("/<org:org>/discussions/", endpoint="org_discussions")
class OrgDiscussionsAPI(API):
    @api.doc("list_organization_discussions")
    @api.marshal_list_with(discussion_fields)
    def get(self, org):
        """List organization discussions"""
        reuses = Reuse.objects(organization=org).only("id")
        datasets = Dataset.objects(organization=org).only("id")
        subjects = list(reuses) + list(datasets)
        qs = Discussion.objects(subject__in=subjects).order_by("-created")
        return list(qs)


@ns.route("/roles/", endpoint="org_roles")
class OrgRolesAPI(API):
    @api.doc("org_roles")
    @api.marshal_list_with(org_role_fields)
    def get(self):
        """List all possible organization roles"""
        return [{"id": key, "label": value} for (key, value) in ORG_ROLES.items()]
