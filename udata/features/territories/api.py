from udata.api import api, API
from udata.features.territories import check_for_territories

suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The maximum result size',
    location='args', required=False)


@api.route('/territory/suggest/', endpoint='suggest_territory')
class SuggestTerritoriesAPI(API):
    @api.doc('suggest_territory')
    @api.expect(suggest_parser)
    def get(self):
        args = suggest_parser.parse_args()
        territories = check_for_territories(args['q'])
        if args['size']:
            territories = territories[:args['size']]
        return [{
            'id': territory.id,
            'title': territory.name,
            'page': territory.external_url
        } for territory in territories]
