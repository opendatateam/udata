from flask import request

from udata import search
from udata.api import apiv2, API, fields
from udata.utils import multi_to_dict

from .api_fields import reuse_page_fields, reuse_fields
from .search import ReuseSearch
from .models import Reuse

apiv2.inherit('ReusePage', reuse_page_fields)
apiv2.inherit('Reuse', reuse_fields)

ns = apiv2.namespace('reuses', 'Reuse related operations')

search_parser = ReuseSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


@ns.route('/search', endpoint='reuse_search')
class ReuseSearchAPI(API):
    '''Reuses collection search endpoint'''
    @apiv2.doc('search_reuses')
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(reuse_page_fields)
    def get(self):
        '''Search all reuses'''
        search_parser.parse_args()
        return search.query(ReuseSearch, **multi_to_dict(request.args))


suggest_parser = apiv2.parser()
suggest_parser.add_argument(
    'q', help='The string to autocomplete/suggest', location='args',
    required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


reuse_suggestion_fields = apiv2.model('ReuseSuggestion', {
    'id': fields.String(description='The reuse identifier', readonly=True),
    'title': fields.String(description='The reuse title', readonly=True),
    'slug': fields.String(
        description='The reuse permalink string', readonly=True),
    'image_url': fields.String(description='The reuse thumbnail URL'),
    'page': fields.UrlFor(
        'reuses.show_redirect', lambda o: {'reuse': o['slug']},
        description='The reuse page URL', readonly=True, fallback_endpoint='api.reuse')
})


@ns.route('/suggest/', endpoint='suggest_reuses')
class ReusesSuggestAPI(API):
    @apiv2.doc('suggest_reuses')
    @apiv2.expect(suggest_parser)
    @apiv2.marshal_list_with(reuse_suggestion_fields)
    def get(self):
        '''Reuses suggest endpoint using mongoDB contains'''
        args = suggest_parser.parse_args()
        reuses = Reuse.objects(deleted=None, private__ne=True, title__icontains=args['q'])
        return [
            {
                'id': reuse.id,
                'title': reuse.title,
                'slug': reuse.slug,
                'image_url': reuse.image_url,
            }
            for reuse in reuses.order_by(DEFAULT_SORTING).limit(args['size'])
        ]
