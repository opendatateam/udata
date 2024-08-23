from udata.core.dataset.models import Dataset
from udata.frontend import csv

from .models import Organization


@csv.adapter(Organization)
class OrganizationCsvAdapter(csv.Adapter):
    downloads_counts = None

    fields = (
        "id",
        "name",
        "acronym",
        "slug",
        ("url", "external_url"),
        "description",
        ("logo", lambda o: o.logo(external=True)),
        ("badges", lambda o: ",".join([badge.kind for badge in o.badges])),
        "created_at",
        "last_modified",
        "business_number_id",
        ("members_count", lambda o: len(o.members)),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Organization) + self.get_dynamic_field_downloads()

    def get_dynamic_field_downloads(self):
        downloads_counts = self.get_downloads_counts()
        return [("downloads", lambda o: downloads_counts.get(str(o.id), 0))]

    def get_downloads_counts(self):
        """
        Prefetch all the resources' downloads for all selected organization into memory
        """
        if self.downloads_counts is not None:
            return self.downloads_counts

        self.downloads_counts = {}

        ids = [o.id for o in self.queryset]
        for dataset in Dataset.objects(organization__in=ids):
            org_id = str(dataset.organization.id)
            if self.downloads_counts.get(org_id) is None:
                self.downloads_counts[org_id] = 0

            self.downloads_counts[org_id] += sum(
                resource.metrics.get("views", 0) for resource in dataset.resources
            )

        return self.downloads_counts
