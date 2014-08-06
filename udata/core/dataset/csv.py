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
        'organization',
        'supplier',
        'description',
        'frequency',
        'license',
        'private',
        'featured',
        'created_at',
        'last_modified',
        ('tags', lambda o: ','.join(o.tags)),
    )

    def dynamic_fields(self):
        return csv.metric_fields(Dataset)
