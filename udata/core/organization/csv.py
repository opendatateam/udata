from udata.core.dataset.models import Dataset
from udata.frontend import csv

from .models import Organization


@csv.adapter(Organization)
class OrganizationCsvAdapter(csv.Adapter):
    downloads_counts = None

    fields = (
        'id',
        'name',
        'slug',
        ('url', 'external_url'),
        'description',
        ('logo', lambda o: o.logo(external=True)),
        ('badges', lambda o: [badge.kind for badge in o.badges]),
        'created_at',
        'last_modified',
    )

    def dynamic_fields(self):
        self.get_downloads_counts()
        return csv.metric_fields(Organization)
    
    def get_downloads_counts(self):
        if self.downloads_counts is not None:
            return self.downloads_counts

        self.downloads_counts = {}

        ids = [o.id for o in self.queryset]
        for dataset in Dataset.objects(organization__in=ids):
            if self.downloads_counts.get(dataset.organization) is None:
                self.downloads_counts[dataset.organization] = 0

            self.downloads_counts[dataset.organization] += sum(resource.metrics.get('views', 0) for resource in dataset.resources)

        return {}
