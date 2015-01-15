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
        'organization',
        ('image', lambda o: o.image(external=True)),
        ('featured', lambda o: o.featured or False),
        'created_at',
        'last_modified',
        ('tags', lambda o: ','.join(o.tags)),
        ('datasets', lambda o: ','.join([str(d.id) for d in o.datasets])),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Reuse)
