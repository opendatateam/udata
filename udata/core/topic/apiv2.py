import logging

import mongoengine
from bson import ObjectId
from flask import request, url_for

from udata.api import API, apiv2, fields
from udata.core.dataset.api import DatasetApiParser
from udata.core.dataset.apiv2 import dataset_page_fields
from udata.core.dataset.models import Dataset
from udata.core.organization.api_fields import org_ref_fields
from udata.core.reuse.api import ReuseApiParser
from udata.core.reuse.models import Reuse
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.topic.models import Topic
from udata.core.topic.parsers import TopicApiParser
from udata.core.topic.permissions import TopicEditPermission
from udata.core.user.api_fields import user_ref_fields

DEFAULT_SORTING = "-created_at"
DEFAULT_PAGE_SIZE = 20

log = logging.getLogger(__name__)

ns = apiv2.namespace("topics", "Topics related operations")

topic_parser = TopicApiParser()
generic_parser = apiv2.page_parser()
dataset_parser = DatasetApiParser()
reuse_parser = ReuseApiParser()

common_doc = {"params": {"topic": "The topic ID"}}


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
        "datasets": fields.Raw(
            attribute=lambda o: {
                "rel": "subsection",
                "href": url_for(
                    "apiv2.topic_datasets",
                    topic=o.id,
                    page=1,
                    page_size=DEFAULT_PAGE_SIZE,
                    _external=True,
                ),
                "type": "GET",
                "total": len(o.datasets),
            },
            description="Link to the topic datasets",
        ),
        "reuses": fields.Raw(
            attribute=lambda o: {
                "rel": "subsection",
                "href": url_for(
                    "apiv2.topic_reuses",
                    topic=o.id,
                    page=1,
                    page_size=DEFAULT_PAGE_SIZE,
                    _external=True,
                ),
                "type": "GET",
                "total": len(o.reuses),
            },
            description="Link to the topic reuses",
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


@ns.route("/", endpoint="topics_list")
class TopicsAPI(API):
    @apiv2.expect(topic_parser.parser)
    @apiv2.marshal_with(topic_page_fields)
    def get(self):
        """List all topics"""
        args = topic_parser.parse()
        topics = Topic.objects()
        topics = topic_parser.parse_filters(topics, args)
        sort = args["sort"] or ("$text_score" if args["q"] else None) or DEFAULT_SORTING
        return topics.order_by(sort).paginate(args["page"], args["page_size"])


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


@ns.route("/<topic:topic>/datasets/", endpoint="topic_datasets", doc=common_doc)
class TopicDatasetsAPI(API):
    @apiv2.doc("topic_datasets")
    @apiv2.expect(dataset_parser.parser)
    @apiv2.marshal_with(dataset_page_fields)
    def get(self, topic):
        """Get a given topic datasets, with filters"""
        args = dataset_parser.parse()
        args["topic"] = topic.id
        datasets = Dataset.objects(archived=None, deleted=None, private=False)
        datasets = dataset_parser.parse_filters(datasets, args)
        sort = args["sort"] or ("$text_score" if args["q"] else None) or "-created_at_internal"
        return datasets.order_by(sort).paginate(args["page"], args["page_size"])

    @apiv2.secure
    @apiv2.doc("topic_datasets_create")
    @apiv2.expect([topic_add_items_fields])
    @apiv2.marshal_with(topic_fields)
    @apiv2.response(400, "Malformed object id(s) in request")
    @apiv2.response(400, "Expecting a list")
    @apiv2.response(400, "Expecting a list of dicts with id attribute")
    @apiv2.response(404, "Topic not found")
    @apiv2.response(403, "Forbidden")
    def post(self, topic):
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        data = request.json

        if not isinstance(data, list):
            apiv2.abort(400, "Expecting a list")
        if not all(isinstance(d, dict) and d.get("id") for d in data):
            apiv2.abort(400, "Expecting a list of dicts with id attribute")

        try:
            datasets = Dataset.objects.filter(id__in=[d["id"] for d in data]).only("id")
            diff = set(d.id for d in datasets) - set(d.id for d in topic.datasets)
        except mongoengine.errors.ValidationError:
            apiv2.abort(400, "Malformed object id(s) in request")

        if diff:
            topic.datasets += [ObjectId(did) for did in diff]
            topic.save()

        return topic, 201


@ns.route(
    "/<topic:topic>/datasets/<dataset:dataset>/",
    endpoint="topic_dataset",
    doc={"params": {"topic": "The topic ID", "dataset": "The dataset ID"}},
)
class TopicDatasetAPI(API):
    @apiv2.secure
    @apiv2.response(404, "Topic not found")
    @apiv2.response(404, "Dataset not found in topic")
    @apiv2.response(204, "Success")
    def delete(self, topic, dataset):
        """Delete a given dataset from the given topic"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        if dataset.id not in (d.id for d in topic.datasets):
            apiv2.abort(404, "Dataset not found in topic")
        topic.datasets = [d for d in topic.datasets if d.id != dataset.id]
        topic.save()

        return None, 204


@ns.route("/<topic:topic>/reuses/", endpoint="topic_reuses", doc=common_doc)
class TopicReusesAPI(API):
    @apiv2.doc("topic_reuses")
    @apiv2.expect(reuse_parser.parser)
    @apiv2.marshal_with(Reuse.__page_fields__)
    def get(self, topic):
        """Get a given topic reuses, with filters"""
        args = reuse_parser.parse()
        reuses = Reuse.objects(deleted=None, private__ne=True).filter(
            id__in=[d.id for d in topic.reuses]
        )
        # warning: topic in reuse_parser is different from Topic
        reuses = reuse_parser.parse_filters(reuses, args)
        sort = args["sort"] or ("$text_score" if args["q"] else None) or DEFAULT_SORTING
        return reuses.order_by(sort).paginate(args["page"], args["page_size"])

    @apiv2.secure
    @apiv2.doc("topic_reuses_create")
    @apiv2.expect([topic_add_items_fields])
    @apiv2.marshal_with(topic_fields)
    @apiv2.response(400, "Malformed object id(s) in request")
    @apiv2.response(400, "Expecting a list")
    @apiv2.response(400, "Expecting a list of dicts with id attribute")
    @apiv2.response(404, "Topic not found")
    @apiv2.response(403, "Forbidden")
    def post(self, topic):
        """Add reuses to a given topic from a list of reuses ids"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        data = request.json

        if not isinstance(data, list):
            apiv2.abort(400, "Expecting a list")
        if not all(isinstance(d, dict) and d.get("id") for d in data):
            apiv2.abort(400, "Expecting a list of dicts with id attribute")

        try:
            reuses = Reuse.objects.filter(id__in=[r["id"] for r in data]).only("id")
            diff = set(d.id for d in reuses) - set(d.id for d in topic.reuses)
        except mongoengine.errors.ValidationError:
            apiv2.abort(400, "Malformed object id(s) in request")

        if diff:
            topic.reuses += [ObjectId(rid) for rid in diff]
            topic.save()

        return topic, 201


@ns.route(
    "/<topic:topic>/reuses/<reuse:reuse>/",
    endpoint="topic_reuse",
    doc={"params": {"topic": "The topic ID", "reuse": "The reuse ID"}},
)
class TopicReuseAPI(API):
    @apiv2.secure
    @apiv2.response(404, "Topic not found")
    @apiv2.response(404, "Reuse not found in topic")
    @apiv2.response(204, "Success")
    def delete(self, topic, reuse):
        """Delete a given reuse from the given topic"""
        if not TopicEditPermission(topic).can():
            apiv2.abort(403, "Forbidden")

        if reuse.id not in (d.id for d in topic.reuses):
            apiv2.abort(404, "Reuse not found in topic")
        topic.reuses = [d for d in topic.reuses if d.id != reuse.id]
        topic.save()

        return None, 204
