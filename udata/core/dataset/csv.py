from udata.core.discussions.models import Discussion
from udata.frontend import csv

from .models import Dataset, Resource


def serialize_spatial_zones(dataset):
    if dataset.spatial and dataset.spatial.zones:
        return ','.join(z.name for z in dataset.spatial.zones)


@csv.adapter(Dataset)
class DatasetCsvAdapter(csv.Adapter):
    fields = (
        'id',
        'title',
        'slug',
        'acronym',
        ('url', 'external_url'),
        ('organization', 'organization.name'),
        ('organization_id', 'organization.id'),
        'description',
        'frequency',
        'license',
        'temporal_coverage.start',
        'temporal_coverage.end',
        'spatial.granularity',
        ('spatial.zones', serialize_spatial_zones),
        'private',
        ('featured', lambda o: o.featured or False),
        'created_at',
        'last_modified',
        ('tags', lambda o: ','.join(o.tags)),
        ('archived', lambda o: o.archived or False),
        ('resources_count', lambda o: len(o.resources)),
        ('harvest.backend', lambda r: r.harvest and r.harvest.backend),
        ('harvest.domain', lambda r: r.harvest and r.harvest.domain),
        ('harvest.created_at', lambda r: r.harvest and r.harvest.created_at),
        ('harvest.modified_at', lambda r: r.harvest and r.harvest.modified_at),
        ('quality_score', lambda o: format(o.quality['score'], '.2f')),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Dataset)


def dataset_field(name, getter=None):
    return ('dataset.{0}'.format(name), getter or name)


@csv.adapter(Resource)
class ResourcesCsvAdapter(csv.NestedAdapter):
    fields = (
        dataset_field('id'),
        dataset_field('title'),
        dataset_field('slug'),
        dataset_field('url', 'external_url'),
        dataset_field(
            'organization',
            lambda r: r.organization.name if r.organization else None),
        dataset_field(
            'organization_id',
            lambda r: str(r.organization.id) if r.organization else None),
        dataset_field('license'),
        dataset_field('private'),
        dataset_field(
            'archived',
            lambda r: r.archived or False),
    )
    nested_fields = (
        'id',
        'url',
        'title',
        'description',
        'filetype',
        'format',
        'mime',
        'filesize',
        ('checksum.type', lambda o: getattr(o.checksum, 'type', None)),
        ('checksum.value', lambda o: getattr(o.checksum, 'value', None)),
        'created_at',
        ('modified', lambda o: o.last_modified),
        ('downloads', lambda o: int(o.metrics.get('views', 0))),
        ('harvest.created_at', lambda o: o.harvest and o.harvest.created_at),
        ('harvest.modified_at', lambda o: o.harvest and o.harvest.modified_at),
    )
    attribute = 'resources'


@csv.adapter(Discussion)
class DiscussionCsvAdapter(csv.Adapter):
    fields = (
        'id',
        'user',
        'subject',
        'title',
        ('size', lambda o: len(o.discussion)),
        ('messages', lambda o: '\n'.join(msg.content for msg in o.discussion)),
        'created',
        'closed',
        'closed_by',
    )
