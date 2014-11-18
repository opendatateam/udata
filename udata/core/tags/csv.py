# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend import csv

from .models import Tag


def counts(name):
    return (name, lambda o: int(o.counts.get(name, 0)))


@csv.adapter(Tag)
class TagCsvAdapter(csv.Adapter):
    fields = (
        'name',
        counts('datasets'),
        counts('reuses'),
        'total',
    )
