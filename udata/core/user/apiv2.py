from flask_security import current_user

from udata.api import API, apiv2
from udata.core.topic.apiv2 import topic_page_fields
from udata.core.topic.parsers import TopicApiParser
from udata.models import Topic

me = apiv2.namespace("me", "Connected user related operations (v2)")

# we will force include_private to True, no need for this arg
topic_parser = TopicApiParser(with_include_private=False)


@me.route("/org_topics/", endpoint="my_org_topics")
class MyOrgTopicsAPI(API):
    @apiv2.secure
    @apiv2.doc("my_org_topics")
    @apiv2.expect(topic_parser.parser)
    @apiv2.marshal_list_with(topic_page_fields)
    def get(self):
        """List all topics related to me and my organizations."""
        args = topic_parser.parse()
        args["include_private"] = True
        owners = list(current_user.organizations) + [current_user.id]
        topics = Topic.objects.owned_by(*owners)
        topics = topic_parser.parse_filters(topics, args)
        sort = args["sort"] or ("$text_score" if args["q"] else None) or "-last-modified"
        return topics.order_by(sort).paginate(args["page"], args["page_size"])
