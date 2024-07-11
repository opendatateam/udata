from udata.frontend import csv

from .models import Reuse


@csv.adapter(Reuse)
class ReuseCsvAdapter(csv.Adapter):
    fields = (
        "id",
        "title",
        "slug",
        ("url", "external_url"),
        "type",
        "description",
        ("remote_url", "url"),
        ("organization", "organization.name"),
        ("organization_id", "organization.id"),
        ("owner", "owner.slug"),  # in case it's owned by a user
        ("owner_id", "owner.id"),
        ("image", lambda r: r.image(external=True)),
        ("featured", lambda r: r.featured or False),
        "created_at",
        "last_modified",
        ("archived", lambda r: r.archived or False),
        "topic",
        ("tags", lambda r: ",".join(r.tags)),
        ("datasets", lambda r: ",".join([str(d.id) for d in r.datasets])),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Reuse)
