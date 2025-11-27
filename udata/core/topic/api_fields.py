from flask import url_for

from udata.api import api, apiv2, fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.topic import DEFAULT_PAGE_SIZE
from udata.core.user.api_fields import user_ref_fields

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
                "total": o.elements.count(),
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
        "uri": fields.String(
            attribute=lambda t: url_for("apiv2.topic", topic=t, _external=True),
            description="The topic API URI",
            readonly=True,
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
    },
)

topic_page_fields = apiv2.model("TopicPage", fields.pager(topic_fields))

element_fields = apiv2.model(
    "TopicElement",
    {
        "id": fields.String(description="The element id"),
        "title": fields.String(description="The element title"),
        "description": fields.String(description="The element description"),
        "tags": fields.List(fields.String, description="The element tags"),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
        "element": fields.Nested(
            api.model_reference, description="The element target object", allow_null=True
        ),
    },
)

element_page_fields = apiv2.model("TopicElementPage", fields.pager(element_fields))

topic_input_fields = apiv2.clone(
    "TopicInput",
    topic_fields,
    {
        "elements": fields.List(fields.Nested(element_fields, description="The topic elements")),
    },
)
