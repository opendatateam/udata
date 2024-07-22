from udata.frontend import csv

from .models import HarvestSource


@csv.adapter(HarvestSource)
class HarvestSourceCsvAdapter(csv.Adapter):
    fields = (
        "id",
        "name",
        "url",
        ("organization", "organization.name"),
        ("organization_id", "organization.id"),
        "backend",
        "created_at",
        ("validation", lambda o: o.validation.state),
    )
