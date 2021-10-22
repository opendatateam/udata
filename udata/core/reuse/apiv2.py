from flask import request

from udata import search
from udata.api import apiv2, API
from udata.utils import multi_to_dict

from .api_fields import reuse_page_fields
from .search import ReuseSearch

ns = apiv2.namespace('reuses', 'Reuse related operations')

common_doc = {
    'params': {'reuse': 'The reuse ID or slug'}
}
search_parser = ReuseSearch.as_request_parser()


@ns.route('/search', endpoint='reuse_search')
class ReuseSearchAPI(API):
    @apiv2.doc('search_reuses')
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(reuse_page_fields)
    def get(self):
        search_parser.parse_args()
        return search.query(ReuseSearch, **multi_to_dict(request.args))
