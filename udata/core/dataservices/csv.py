from udata.core import csv

from .models import Dataservice


@csv.adapter(Dataservice)
class DataserviceCsvAdapter(csv.Adapter):
    fields = (
        "id",
        "title",
        "slug",
        "acronym",
        ("url", lambda d: d.self_web_url()),
        "description",
        "base_api_url",
        "machine_documentation_url",
        "technical_documentation_url",
        "business_documentation_url",
        "authorization_request_url",
        "availability",
        "rate_limiting",
        "access_type",
        "license",
        ("organization", "organization.name"),
        ("organization_id", "organization.id"),
        ("owner", "owner.slug"),  # in case it's owned by a user
        ("owner_id", "owner.id"),
        "created_at",
        "metadata_modified_at",
        ("archived", lambda d: d.archived_at or False),
        ("tags", lambda d: ",".join(d.tags)),
        ("datasets", lambda d: ",".join([str(d.id) for d in d.datasets])),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Dataservice)
