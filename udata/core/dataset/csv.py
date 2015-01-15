# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend import csv

from .models import Dataset


@csv.adapter(Dataset)
class DatasetCsvAdapter(csv.Adapter):
    fields = (
        'id',
        'title',
        'slug',
        ('url', 'external_url'),
        ('organization', lambda r: r.organization.name if r.organization else None),
        ('organization_id', lambda r: str(r.organization.id) if r.organization else None),
        'supplier',
        'description',
        'frequency',
        'license',
        'private',
        ('featured', lambda o: o.featured or False),
        'created_at',
        'last_modified',
        ('tags', lambda o: ','.join(o.tags)),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Dataset)


def dataset_field(name, getter=None):
    return ('dataset.{0}'.format(name), getter or name)


class ResourcesCsvAdapter(csv.NestedAdapter):
    fields = (
        dataset_field('id'),
        dataset_field('title'),
        dataset_field('slug'),
        dataset_field('url', 'external_url'),
        dataset_field('organization', lambda r: r.organization.name if r.organization else None),
        dataset_field('organization_id', lambda r: str(r.organization.id) if r.organization else None),
        dataset_field('license'),
        dataset_field('private'),
    )
    nested_fields = (
        'id',
        'url',
        'title',
        'description',
        'type',
        'format',
        'mime',
        'size',
        ('checksum.type', lambda o: getattr(o.checksum, 'type', None)),
        ('checksum.value', lambda o: getattr(o.checksum, 'value', None)),
        'created_at',
        'modified',
        ('downloads', lambda o: int(o.metrics.get('views', 0))),
    )
    attribute = 'resources'
