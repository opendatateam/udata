import logging

import mongoengine
from flask import request, url_for
from flask_security import current_user

from udata.api import API, apiv2, fields
from udata.core.dataset.api import DatasetApiParser
from udata.core.discussions.models import Discussion
from udata.core.reuse.api import ReuseApiParser
from udata.core.topic.api_fields import element_page_fields, topic_fields, topic_page_fields
from udata.core.topic.forms import TopicElementForm, TopicForm
from udata.core.topic.models import Topic, TopicElement
from udata.core.topic.parsers import TopicApiParser, elements_parser
from udata.core.topic.permissions import TopicEditPermission
from udata.utils import get_by

DEFAULT_SORTING = "-created_at"

log = logging.getLogger(__name__)

ns = apiv2.namespace("topics", "Topics related operations")

topic_parser = TopicApiParser()
generic_parser = apiv2.page_parser()
dataset_parser = DatasetApiParser()
reuse_parser = ReuseApiParser()

common_doc = {"params": {"topic": "The topic ID"}}


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

    @apiv2.secure
    @apiv2.doc("update_topic")
    @apiv2.expect(topic_fields)
    @apiv2.marshal_with(topic_fields)
    @apiv2.response(400, "Validation error")
    @apiv2.response(403, "Forbidden")
    def put(self, topic):
        """Update a given topic"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")
        form = apiv2.validate(TopicForm, topic)
        return form.save()

    @apiv2.secure
    @apiv2.doc("delete_topic")
    @apiv2.response(204, "Object deleted")
    @apiv2.response(403, "Forbidden")
    def delete(self, topic):
        """Delete a given topic"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")
        # Remove discussions linked to the topic
        Discussion.objects(subject=topic).delete()
        topic.delete()
        return "", 204


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
