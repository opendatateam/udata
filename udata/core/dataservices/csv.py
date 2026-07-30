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
        ("featured", lambda d: d.featured or False),
        "created_at",
        "metadata_modified_at",
        ("archived", lambda d: d.archived_at or False),
        ("tags", lambda d: ",".join(d.tags)),
        ("datasets", lambda d: ",".join([str(d.id) for d in d.datasets])),
        ("harvest.backend", lambda r: r.harvest and r.harvest.backend),
        ("harvest.domain", lambda r: r.harvest and r.harvest.domain),
        ("harvest.remote_id", lambda r: r.harvest and r.harvest.remote_id),
        ("harvest.remote_url", lambda r: r.harvest and r.harvest.remote_url),
        ("harvest.uri", lambda r: r.harvest and r.harvest.uri),
        ("harvest.created_at", lambda r: r.harvest and r.harvest.created_at),
        ("harvest.issued_at", lambda r: r.harvest and r.harvest.issued_at),
        ("harvest.modified_at", lambda r: r.harvest and r.harvest.modified_at),
        ("harvest.last_update", lambda r: r.harvest and r.harvest.last_update),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Dataservice)
