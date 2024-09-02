import mongoengine
from flask import request

from udata import search
from udata.api import API, apiv2
from udata.core.contact_point.api_fields import contact_point_fields
from udata.utils import multi_to_dict

from .api_fields import member_fields, org_fields, org_page_fields
from .permissions import EditOrganizationPermission
from .search import OrganizationSearch

apiv2.inherit("OrganizationPage", org_page_fields)
apiv2.inherit("Organization", org_fields)
apiv2.inherit("Member", member_fields)
apiv2.inherit("ContactPoint", contact_point_fields)


ns = apiv2.namespace("organizations", "Organization related operations")
search_parser = OrganizationSearch.as_request_parser()

DEFAULT_SORTING = "-created_at"


@ns.route("/search/", endpoint="organization_search")
class OrganizationSearchAPI(API):
    """Organizations collection search endpoint"""

    @apiv2.doc("search_organizations")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(org_page_fields)
    def get(self):
        """Search all organizations"""
        search_parser.parse_args()
        return search.query(OrganizationSearch, **multi_to_dict(request.args))


@ns.route("/<org:org>/extras/", endpoint="organization_extras")
@apiv2.response(400, "Wrong payload format, dict expected")
@apiv2.response(400, "Wrong payload format, list expected")
@apiv2.response(404, "Organization not found")
@apiv2.response(410, "Organization has been deleted")
class OrganizationExtrasAPI(API):
    @apiv2.doc("get_organization_extras")
    def get(self, org):
        """Get an organization extras given its identifier"""
        if org.deleted:
            apiv2.abort(410, "Organization has been deleted")
        return org.extras

    @apiv2.secure
    @apiv2.doc("update_organization_extras")
    def put(self, org):
        """Update a given organization extras"""
        data = request.json
        if not isinstance(data, dict):
            apiv2.abort(400, "Wrong payload format, dict expected")
        if org.deleted:
            apiv2.abort(410, "Organization has been deleted")
        EditOrganizationPermission(org).test()
        # first remove extras key associated to a None value in payload
        for key in [k for k in data if data[k] is None]:
            org.extras.pop(key, None)
            data.pop(key)

        # then update the extras with the remaining payload
        org.extras.update(data)
        try:
            org.save()
        except mongoengine.errors.ValidationError as e:
            apiv2.abort(400, e.message)
        return org.extras

    @apiv2.secure
    @apiv2.doc("delete_organization_extras")
    def delete(self, org):
        """Delete a given organization extras key on a given organization"""
        data = request.json
        if not isinstance(data, list):
            apiv2.abort(400, "Wrong payload format, list expected")
        if org.deleted:
            apiv2.abort(410, "Organization has been deleted")
        EditOrganizationPermission(org).test()
        for key in data:
            try:
                del org.extras[key]
            except KeyError:
                pass
        org.save()
        return org.extras, 204
