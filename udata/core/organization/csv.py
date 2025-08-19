from udata.core import csv
from udata.core.dataset.models import Dataset

from .models import Organization


def get_resource_download_count(organization: Organization) -> int:
    return sum(
        dat.metrics.get("resources_downloads", 0) or 0
        for dat in Dataset.objects(organization=organization).only("metrics").visible()
    )


@csv.adapter(Organization)
class OrganizationCsvAdapter(csv.Adapter):
    downloads_counts = None

    fields = (
        "id",
        "name",
        "acronym",
        "slug",
        ("url", lambda o: o.url_for()),
        "description",
        ("logo", lambda o: o.logo(external=True)),
        ("badges", lambda o: ",".join([badge.kind for badge in o.badges])),
        "created_at",
        "last_modified",
        "business_number_id",
        ("members_count", lambda o: len(o.members)),
        ("downloads", get_resource_download_count),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Organization)
