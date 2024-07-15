from udata.api import api, API

from udata.tags import slug  # TODO: merge this into this package
from udata.models import Tag

DEFAULT_SIZE = 8

ns = api.namespace('tags', 'Tags related operations')

parser = api.parser()
parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=DEFAULT_SIZE)


@ns.route('/suggest/', endpoint='suggest_tags')
class SuggestTagsAPI(API):
    @api.doc('suggest_tags')
    @api.expect(parser)
    def get(self):
        '''Suggest tags'''
        args = parser.parse_args()
        q = slug(args['q'])
        results = [{'text': i.name} for i in Tag.objects(name__icontains=q).limit(args['size'])]
        return sorted(results, key=lambda o: len(o['text']))
