from flask import request

from udata import search
from udata.api import apiv2, API
from udata.utils import multi_to_dict
from .search import OrganizationSearch
from .api_fields import org_page_fields, org_fields, member_fields
from .models import Organization

apiv2.inherit('OrganizationPage', org_page_fields)
apiv2.inherit('Organization', org_fields)
apiv2.inherit('Member', member_fields)


ns = apiv2.namespace('organizations', 'Organization related operations')
search_parser = OrganizationSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


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


suggest_parser = apiv2.parser()
suggest_parser.add_argument(
    'q', help='The string to autocomplete/suggest', location='args',
    required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_organizations')
class OrganizationSuggestAPI(API):
    @apiv2.doc('suggest_organizations')
    @apiv2.expect(suggest_parser)
    @apiv2.marshal_list_with(org_suggestion_fields)
    def get(self):
        '''Organizations suggest endpoint using mongoDB contains'''
        args = suggest_parser.parse_args()
        orgs = Organization.objects(deleted=None, name__icontains=args['q'])
        return [
            {
                'id': org.id,
                'title': org.title,
                'acronym': org.acronym,
                'slug': org.slug,
                'image_url': org.image_url,
            }
            for org in orgs.order_by(DEFAULT_SORTING).limit(args['size'])
        ]
