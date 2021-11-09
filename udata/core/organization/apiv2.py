from flask import request

from udata import search
from udata.api import apiv2, API
from udata.utils import multi_to_dict
from .search import OrganizationSearch
from .api_fields import org_page_fields

from udata.core.dataset.search import DatasetSearch

ns = apiv2.namespace('organizations', 'Organization related operations')
search_parser = OrganizationSearch.as_request_parser()


@ns.route('/search', endpoint='organization_search')
class OrganizationSearchAPI(API):
    '''Organizations collection search endpoint'''
    @apiv2.doc('search_organizations')
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(org_page_fields)
    def get(self):
        '''Search all organizations'''
        search_parser.parse_args()
        return search.query(OrganizationSearch, **multi_to_dict(request.args))
