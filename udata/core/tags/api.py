from udata.api import API, api
from udata.core.suggest import mongo_suggest
from udata.models import Tag

DEFAULT_SIZE = 8

ns = api.namespace("tags", "Tags related operations")

parser = api.parser()
parser.add_argument(
    "q", type=str, help="The string to autocomplete/suggest", location="args", required=True
)
parser.add_argument(
    "size",
    type=int,
    help="The amount of suggestion to fetch",
    location="args",
    default=DEFAULT_SIZE,
)


@ns.route("/suggest/", endpoint="suggest_tags")
class SuggestTagsAPI(API):
    @api.doc("suggest_tags")
    @api.expect(parser)
    def get(self):
        """Suggest tags, ranked by match quality (exact > prefix > word > substring)."""
        args = parser.parse_args()
        tags = mongo_suggest(
            Tag.objects,
            args["q"],
            match_fields=["name"],
            slug_field="name",
            size=args["size"],
        )
        return [{"text": tag.name} for tag in tags]
