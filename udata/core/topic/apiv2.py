import logging

import mongoengine
from flask import request, url_for
from flask_security import current_user

from udata.api import API, apiv2, fields
from udata.core.dataset.api import DatasetApiParser
from udata.core.organization.api_fields import org_ref_fields
from udata.core.reuse.api import ReuseApiParser
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.topic.forms import TopicElementForm, TopicForm
from udata.core.topic.models import Topic, TopicElement
from udata.core.topic.parsers import TopicApiParser
from udata.core.topic.permissions import TopicEditPermission
from udata.core.user.api_fields import user_ref_fields
from udata.utils import get_by

DEFAULT_SORTING = "-created_at"
DEFAULT_PAGE_SIZE = 20

log = logging.getLogger(__name__)

ns = apiv2.namespace("topics", "Topics related operations")

topic_parser = TopicApiParser()
generic_parser = apiv2.page_parser()
dataset_parser = DatasetApiParser()
reuse_parser = ReuseApiParser()

common_doc = {"params": {"topic": "The topic ID"}}


# FIXME: move to fields submodule
topic_fields = apiv2.model(
    "Topic",
    {
        "id": fields.String(description="The topic identifier"),
        "name": fields.String(description="The topic name", required=True),
        "slug": fields.String(description="The topic permalink string", readonly=True),
        "description": fields.Markdown(
            description="The topic description in Markdown", required=True
        ),
        "tags": fields.List(
            fields.String, description="Some keywords to help in search", required=True
        ),
        # FIXME: that won't work for input serialiazation, we need smtg like for resources:
        # "resources": fields.List(
        #     fields.Nested(resource_fields, description="The dataset resources")
        # ),
        "elements": fields.Raw(
            attribute=lambda o: {
                "rel": "subsection",
                "href": url_for(
                    "apiv2.topic_elements",
                    topic=o.id,
                    page=1,
                    page_size=DEFAULT_PAGE_SIZE,
                    _external=True,
                ),
                "type": "GET",
                "total": len(o.elements),
            },
            description="Link to the topic elements",
        ),
        "featured": fields.Boolean(description="Is the topic featured"),
        "private": fields.Boolean(description="Is the topic private"),
        "created_at": fields.ISODateTime(description="The topic creation date", readonly=True),
        "spatial": fields.Nested(
            spatial_coverage_fields, allow_null=True, description="The spatial coverage"
        ),
        "last_modified": fields.ISODateTime(
            description="The topic last modification date", readonly=True
        ),
        "organization": fields.Nested(
            org_ref_fields,
            allow_null=True,
            description="The publishing organization",
            readonly=True,
        ),
        "owner": fields.Nested(
            user_ref_fields, description="The owner user", readonly=True, allow_null=True
        ),
        "uri": fields.UrlFor(
            "api.topic", lambda o: {"topic": o}, description="The topic API URI", readonly=True
        ),
        "page": fields.UrlFor(
            "topics.display",
            lambda o: {"topic": o},
            description="The topic page URL",
            readonly=True,
            fallback_endpoint="api.topic",
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
    },
)

topic_page_fields = apiv2.model("TopicPage", fields.pager(topic_fields))

nested_element_fields = apiv2.model(
    "NestedTopicElement",
    {
        "class": fields.ClassName(description="The model class", required=True),
        "id": fields.String(description="The object identifier", required=True),
    },
)

element_fields = apiv2.model(
    "TopicElement",
    {
        "id": fields.String(description="The element id"),
        "title": fields.String(description="The element title"),
        "description": fields.String(description="The element description"),
        "element": fields.Nested(nested_element_fields, description="The element target object"),
    },
)

element_page_fields = apiv2.model(
    "TopicElementPage",
    {
        "data": fields.List(fields.Nested(element_fields, description="The topic elements")),
        "next_page": fields.String(),
        "previous_page": fields.String(),
        "page": fields.Integer(),
        "page_size": fields.Integer(),
        "total": fields.Integer(),
    },
)

# FIXME: move to parsers submodule
elements_parser = apiv2.parser()
elements_parser.add_argument("page", type=int, default=1, location="args", help="The page to fetch")
elements_parser.add_argument(
    "page_size", type=int, default=DEFAULT_PAGE_SIZE, location="args", help="The page size to fetch"
)
elements_parser.add_argument(
    "type", type=str, location="args", help="The type of resources to fetch"
)
elements_parser.add_argument(
    "q", type=str, location="args", help="query string to search through elements"
)


@ns.route("/", endpoint="topics_list")
class TopicsAPI(API):
    @apiv2.expect(topic_parser.parser)
    @apiv2.marshal_with(topic_page_fields)
    def get(self):
        """List all topics"""
        args = topic_parser.parse()
        topics = Topic.objects.visible_by_user(current_user, mongoengine.Q(private__ne=True))
        topics = topic_parser.parse_filters(topics, args)
        sort = args["sort"] or ("$text_score" if args["q"] else None) or DEFAULT_SORTING
        return topics.order_by(sort).paginate(args["page"], args["page_size"])

    @apiv2.secure
    @apiv2.doc("create_topic")
    @apiv2.expect(topic_fields)
    @apiv2.marshal_with(topic_fields)
    @apiv2.response(400, "Validation error")
    def post(self):
        """Create a topic"""
        form = apiv2.validate(TopicForm)
        return form.save(), 201


@ns.route("/<topic:topic>/", endpoint="topic", doc=common_doc)
@apiv2.response(404, "Topic not found")
class TopicAPI(API):
    @apiv2.doc("get_topic")
    @apiv2.marshal_with(topic_fields)
    def get(self, topic):
        """Get a given topic"""
        return topic


topic_add_items_fields = apiv2.model(
    "TopicItemsAdd",
    {
        "id": fields.String(description="Id of the item to add", required=True),
    },
    location="json",
)


@ns.route("/<topic:topic>/elements/", endpoint="topic_elements", doc=common_doc)
class TopicElementsAPI(API):
    @apiv2.doc("topic_elements")
    @apiv2.expect(elements_parser)
    @apiv2.marshal_with(element_page_fields)
    def get(self, topic):
        """Get a given topic elements, with filters"""
        args = elements_parser.parse_args()
        page = args["page"]
        page_size = args["page_size"]
        list_elements_url = url_for("apiv2.topic_elements", topic=topic.id, _external=True)
        next_page = f"{list_elements_url}?page={page + 1}&page_size={page_size}"
        previous_page = f"{list_elements_url}?page={page - 1}&page_size={page_size}"

        # FIXME: this will probably fail with a lot of elements
        # is there an efficient way to handle embedded documents pagination? or shall we use an Element document?
        # -> aggregation pipeline is probably the way to go
        res = topic.elements

        # FIXME: implement class/type filter
        if args["type"]:
            res = [elem for elem in res if elem["type"] == args["type"]]
            next_page += f"&type={args['type']}"
            previous_page += f"&type={args['type']}"

        # FIXME: implement on description too, and be smarter
        if args["q"]:
            res = [elem for elem in res if args["q"].lower() in elem["title"].lower()]
            next_page += f"&q={args['q']}"
            previous_page += f"&q={args['q']}"

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0
        paginated_result = res[offset : (page_size + offset if page_size is not None else None)]

        print("elements", [e.id for e in topic.elements])

        return {
            "data": paginated_result,
            "next_page": next_page if page_size + offset < len(res) else None,
            "page": page,
            "page_size": page_size,
            "previous_page": previous_page if page > 1 else None,
            "total": len(res),
        }

    @apiv2.secure
    @apiv2.doc("topic_elements_create")
    @apiv2.expect([topic_add_items_fields])
    @apiv2.marshal_with(topic_fields)
    @apiv2.response(400, "Expecting a list")
    @apiv2.response(404, "Topic not found")
    @apiv2.response(403, "Forbidden")
    def post(self, topic):
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        data = request.json

        if not isinstance(data, list):
            apiv2.abort(400, "Expecting a list")

        errors = []
        elements = []
        for element_data in data:
            form = TopicElementForm.from_json(element_data)
            if not form.validate():
                errors.append(form.errors)
            else:
                element = TopicElement()
                form.populate_obj(element)
                elements.append(element)

        if errors:
            apiv2.abort(400, errors=errors)

        for element in elements:
            topic.elements.insert(0, element)

        topic.save()

        return topic, 201


@ns.route(
    "/<topic:topic>/elements/<uuid:element_id>/",
    endpoint="topic_element",
    doc={"params": {"topic": "The topic ID", "element": "The element ID"}},
)
class TopicElementAPI(API):
    @apiv2.secure
    @apiv2.response(404, "Topic not found")
    @apiv2.response(404, "Element not found in topic")
    @apiv2.response(204, "Success")
    def delete(self, topic, element_id):
        """Delete a given element from the given topic"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        element = get_by(topic.elements, "id", element_id)
        if not element:
            apiv2.abort(404, "Element not found in topic")

        topic.elements.remove(element)
        topic.save()

        return None, 204
