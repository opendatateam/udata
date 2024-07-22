from bson.objectid import ObjectId

from udata.api import api
from udata.api.parsers import ModelApiParser


class TopicApiParser(ModelApiParser):
    sorts = {
        "name": "name",
        "created": "created_at",
        "last_modified": "last_modified",
    }

    def __init__(self, with_include_private=True):
        super().__init__()
        if with_include_private:
            self.parser.add_argument("include_private", type=bool, location="args")
        self.parser.add_argument("tag", type=str, location="args")
        self.parser.add_argument("geozone", type=str, location="args")
        self.parser.add_argument("granularity", type=str, location="args")
        self.parser.add_argument("organization", type=str, location="args")
        self.parser.add_argument("owner", type=str, location="args")

    @staticmethod
    def parse_filters(topics, args):
        if args.get("q"):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            topics = topics.search_text(phrase_query)
        if args.get("tag"):
            topics = topics.filter(tags=args["tag"])
        if not args.get("include_private"):
            topics = topics.filter(private=False)
        if args.get("geozone"):
            topics = topics.filter(spatial__zones=args["geozone"])
        if args.get("granularity"):
            topics = topics.filter(spatial__granularity=args["granularity"])
        if args.get("organization"):
            if not ObjectId.is_valid(args["organization"]):
                api.abort(400, "Organization arg must be an identifier")
            topics = topics.filter(organization=args["organization"])
        if args.get("owner"):
            if not ObjectId.is_valid(args["owner"]):
                api.abort(400, "Owner arg must be an identifier")
            topics = topics.filter(owner=args["owner"])
        return topics
