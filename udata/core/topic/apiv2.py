import logging

import mongoengine
from flask import request
from flask_security import current_user

from udata.api import API, api, apiv2
from udata.core.discussions.models import Discussion
from udata.core.topic.api_fields import (
    element_fields,
    element_page_fields,
    topic_fields,
    topic_input_fields,
    topic_page_fields,
)
from udata.core.topic.forms import TopicElementForm, TopicForm
from udata.core.topic.models import Topic, TopicElement
from udata.core.topic.parsers import TopicApiParser, TopicElementsParser
from udata.core.topic.permissions import TopicEditPermission

apiv2.inherit("ModelReference", api.model_reference)

DEFAULT_SORTING = "-created_at"

log = logging.getLogger(__name__)

ns = apiv2.namespace("topics", "Topics related operations")

topic_parser = TopicApiParser()
elements_parser = TopicElementsParser()

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
    @apiv2.expect(topic_input_fields)
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
    @apiv2.expect(topic_input_fields)
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


@ns.route("/<topic:topic>/elements/", endpoint="topic_elements", doc=common_doc)
class TopicElementsAPI(API):
    @apiv2.doc("topic_elements")
    @apiv2.expect(elements_parser.parser)
    @apiv2.marshal_with(element_page_fields)
    def get(self, topic):
        """Get a given topic's elements with pagination."""
        args = elements_parser.parse()
        elements = elements_parser.parse_filters(
            topic.elements,
            args,
        )
        return elements.paginate(args["page"], args["page_size"])

    @apiv2.secure
    @apiv2.doc("topic_elements_create")
    @apiv2.expect([api.model_reference])
    @apiv2.marshal_list_with(element_fields)
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
            form = TopicElementForm.from_json(element_data, meta={"csrf": False})
            if not form.validate():
                errors.append(form.errors)
            else:
                element = TopicElement()
                form.populate_obj(element)
                element.topic = topic
                element.save()
                elements.append(element)

        if errors:
            apiv2.abort(400, errors=errors)

        topic.save()

        return elements, 201

    @apiv2.secure
    @apiv2.doc("topic_elements_delete")
    @apiv2.response(404, "Topic not found")
    @apiv2.response(403, "Forbidden")
    def delete(self, topic):
        """Delete all elements from a Topic

        This a workaround for https://github.com/kvesteri/wtforms-json/issues/43
        -> we can't use PUT /api/2/topics/{topic}/ with an empty list of elements
        """
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        # TODO: this triggers performance issues on a huge topic (too many tasks, too many activities)
        topic.elements.delete()

        return None, 204


@ns.route(
    "/<topic:topic>/elements/<element_id>/",
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

        element = TopicElement.objects.get_or_404(pk=element_id)
        element.delete()

        return None, 204

    @apiv2.secure
    @apiv2.doc("topic_element_update")
    @apiv2.expect(element_fields)
    @apiv2.marshal_with(element_fields)
    @apiv2.response(404, "Topic not found")
    @apiv2.response(404, "Element not found in topic")
    @apiv2.response(204, "Success")
    def put(self, topic, element_id):
        """Update a given element from the given topic"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        element = TopicElement.objects.get_or_404(pk=element_id)
        form = apiv2.validate(TopicElementForm, element)
        form.populate_obj(element)
        element.save()

        return element
