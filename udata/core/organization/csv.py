# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend import csv

from .models import Organization


@csv.adapter(Organization)
class OrganizationCsvAdapter(csv.Adapter):
    fields = (
        'id',
        'name',
        'slug',
        ('url', 'external_url'),
        'description',
        ('logo', lambda o: o.logo(external=True)),
        ('public_service', lambda o: o.public_service or False),
        'created_at',
        'last_modified',
    )

    def dynamic_fields(self):
        return csv.metric_fields(Organization)
