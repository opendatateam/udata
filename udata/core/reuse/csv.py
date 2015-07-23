# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend import csv

from .models import Reuse


@csv.adapter(Reuse)
class ReuseCsvAdapter(csv.Adapter):
    fields = (
        'id',
        'title',
        'slug',
        ('url', 'external_url'),
        'type',
        'description',
        ('remote_url', 'url'),
        ('organization',
         lambda r: r.organization.name if r.organization else None),
        ('organization_id',
         lambda r: str(r.organization.id) if r.organization else None),
        ('image', lambda r: r.image(external=True)),
        ('featured', lambda r: r.featured or False),
        'created_at',
        'last_modified',
        ('tags', lambda r: ','.join(r.tags)),
        ('datasets', lambda r: ','.join([str(d.id) for d in r.datasets])),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Reuse)
