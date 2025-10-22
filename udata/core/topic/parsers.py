from bson.objectid import ObjectId
from flask_restx.inputs import boolean

from udata.api import api
from udata.api.parsers import ModelApiParser
from udata.core.topic import DEFAULT_PAGE_SIZE
from udata.core.topic.models import TopicElement
from udata.mongo.engine import db


class TopicElementsParser(ModelApiParser):
    def __init__(self):
        super().__init__()
        self.parser.add_argument(
            "page", type=int, default=1, location="args", help="The page to fetch"
        )
        self.parser.add_argument(
            "page_size",
            type=int,
            default=DEFAULT_PAGE_SIZE,
            location="args",
            help="The page size to fetch",
        )
        self.parser.add_argument(
            "class",
            type=str,
            location="args",
            help="The class of elements to fetch (eg. Dataset or Reuse)",
        )
        self.parser.add_argument(
            "q", type=str, location="args", help="query string to search through elements"
        )
        self.parser.add_argument("tag", type=str, location="args", action="append")

    @staticmethod
    def parse_filters(elements, args):
        if args.get("q"):
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            elements = elements.search_text(phrase_query)
        if args.get("tag"):
            elements = elements.filter(tags__all=args["tag"])
        if element_class := args.get("class"):
            if element_class == "None":
                elements = elements.filter(element=None)
            else:
                elements = elements.filter(__raw__={"element._cls": element_class})
        return elements


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
        self.parser.add_argument("tag", type=str, location="args", action="append")
        self.parser.add_argument("geozone", type=str, location="args")
        self.parser.add_argument("granularity", type=str, location="args")
        self.parser.add_argument("organization", type=str, location="args")
        self.parser.add_argument("owner", type=str, location="args")
        self.parser.add_argument("featured", type=boolean, location="args")

    @staticmethod
    def parse_filters(topics, args):
        if args.get("q"):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])

            # Search topics by their own content
            topic_text_filter = db.Q(__raw__={"$text": {"$search": phrase_query}})

            # Find topics that have elements matching the search
            matching_elements = TopicElement.objects.search_text(phrase_query)
            element_topic_ids = set(elem.topic.id for elem in matching_elements if elem.topic)

            # Combine with OR
            if element_topic_ids:
                element_filter = db.Q(id__in=element_topic_ids)
                topics = topics.filter(topic_text_filter | element_filter)
            else:
                topics = topics.filter(topic_text_filter)
        if args.get("tag"):
            topics = topics.filter(tags__all=args["tag"])
        if not args.get("include_private"):
            topics = topics.filter(private=False)
        if args.get("geozone"):
            topics = topics.filter(spatial__zones=args["geozone"])
        if args.get("granularity"):
            topics = topics.filter(spatial__granularity=args["granularity"])
        if args.get("featured") is not None:
            topics = topics.filter(featured=args["featured"])
        if args.get("organization"):
            if not ObjectId.is_valid(args["organization"]):
                api.abort(400, "Organization arg must be an identifier")
            topics = topics.filter(organization=args["organization"])
        if args.get("owner"):
            if not ObjectId.is_valid(args["owner"]):
                api.abort(400, "Owner arg must be an identifier")
            topics = topics.filter(owner=args["owner"])
        return topics
