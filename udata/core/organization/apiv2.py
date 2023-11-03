from flask import request

from udata import search
from udata.api import apiv2, API
from udata.utils import multi_to_dict
from .search import OrganizationSearch
from .api_fields import org_page_fields, org_fields, member_fields
from .permissions import (
    EditOrganizationPermission, OrganizationPrivatePermission
)

apiv2.inherit('OrganizationPage', org_page_fields)
apiv2.inherit('Organization', org_fields)
apiv2.inherit('Member', member_fields)


ns = apiv2.namespace('organizations', 'Organization related operations')
search_parser = OrganizationSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


@ns.route('/search/', endpoint='organization_search')
class OrganizationSearchAPI(API):
    '''Organizations collection search endpoint'''
    @apiv2.doc('search_organizations')
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(org_page_fields)
    def get(self):
        '''Search all organizations'''
        search_parser.parse_args()
        return search.query(OrganizationSearch, **multi_to_dict(request.args))


@ns.route('/<org:org>/extras/', endpoint='organization_extras')
@apiv2.response(400, 'Wrong payload format, dict expected')
@apiv2.response(400, 'Wrong payload format, list expected')
@apiv2.response(404, 'Organization not found')
@apiv2.response(410, 'Organization has been deleted')
class DatasetExtrasAPI(API):
    @apiv2.doc('get_organization_extras')
    def get(self, org):
        '''Get a organization extras given its identifier'''
        if org.deleted:
            apiv2.abort(410, 'Dataset has been deleted')
        return org.extras

    @apiv2.secure
    @apiv2.doc('update_organization_extras')
    def put(self, org):
        '''Update a given organization extras'''
        data = request.json
        if not isinstance(data, dict):
            apiv2.abort(400, 'Wrong payload format, dict expected')
        if org.deleted:
            apiv2.abort(410, 'Organization has been deleted')
        EditOrganizationPermission(org).test()
        # first remove extras key associated to a None value in payload
        for key in [k for k in data if data[k] is None and k != 'custom']:
            org.extras.pop(key, None)
            data.pop(key)

        # then update the extras with the remaining payload
        org.extras.update(data)
        org.save()
        return org.extras

    @apiv2.secure
    @apiv2.doc('delete_organization_extras')
    def delete(self, org):
        '''Delete a given organization extras key on a given organization'''
        data = request.json
        if not isinstance(data, list):
            apiv2.abort(400, 'Wrong payload format, list expected')
        if org.deleted:
            apiv2.abort(410, 'Organization has been deleted')
        EditOrganizationPermission(org).test()
        try:
            for key in data:
                del org.extras[key]
        except KeyError:
            apiv2.abort(404, 'Key not found in existing extras')
        org.save()
        return org.extras, 204