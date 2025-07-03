from udata.core import csv

from .models import Tag


def counts(name):
    return (name, lambda o: int(o.counts.get(name, 0)))


@csv.adapter(Tag)
class TagCsvAdapter(csv.Adapter):
    fields = (
        "name",
        counts("datasets"),
        counts("reuses"),
        "total",
    )
