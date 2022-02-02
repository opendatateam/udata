from flask import request

from udata import search
from udata.api import apiv2, API
from udata.utils import multi_to_dict

from .api_fields import reuse_page_fields, reuse_fields
from .search import ReuseSearch

apiv2.inherit('ReusePage', reuse_page_fields)
apiv2.inherit('Reuse', reuse_fields)

ns = apiv2.namespace('reuses', 'Reuse related operations')

search_parser = ReuseSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


@ns.route('/search/', endpoint='reuse_search')
class ReuseSearchAPI(API):
    '''Reuses collection search endpoint'''
    @apiv2.doc('search_reuses')
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(reuse_page_fields)
    def get(self):
        '''Search all reuses'''
        search_parser.parse_args()
        return search.query(ReuseSearch, **multi_to_dict(request.args))
