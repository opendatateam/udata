from udata.api import apiv2, API

from udata.tags import normalize  # TODO: merge this into this package
from udata.models import Tag

DEFAULT_SIZE = 8

ns = apiv2.namespace('tags', 'Tags related operations')

parser = apiv2.parser()
parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=DEFAULT_SIZE)


@ns.route('/suggest/', endpoint='suggest_tags')
class SuggestTagsAPIv2(API):
    @apiv2.doc('suggest_tags')
    @apiv2.expect(parser)
    def get(self):
        '''Suggest tags'''
        args = parser.parse_args()
        q = normalize(args['q'])
        results = [{'text': i.name} for i in Tag.objects(name__icontains=q)]
        return sorted(results, key=lambda o: len(o['text']))
