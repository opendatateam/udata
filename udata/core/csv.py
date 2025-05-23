import csv
import itertools
import logging
from datetime import date, datetime
from io import StringIO

from flask import Response, stream_with_context

from udata.mongo import db
from udata.utils import recursive_get

log = logging.getLogger(__name__)

_adapters = {}

CONFIG = {
    "delimiter": ";",
    "quotechar": '"',
}


def safestr(value):
    """Ensure type to string serialization"""
    if not value or isinstance(value, (int, float, bool)):
        return value
    elif isinstance(value, (date, datetime)):
        return value.isoformat()
    else:
        return str(value)


class Adapter(object):
    """A Base model CSV adapter"""

    fields = None

    def __init__(self, queryset):
        self.queryset = queryset
        self._fields = None

    def get_fields(self):
        if not self._fields:
            if not isinstance(self.fields, (list, tuple)):
                raise ValueError("Unsupported fields format")
            self._fields = []
            for field in itertools.chain(self.fields, self.dynamic_fields()):
                name = field if isinstance(field, str) else field[0]
                # Retrieving (dynamically) fields is prone to errors,
                # we don't want to break the CSV generation for a unique
                # error so we skip it and introduce a blank to the given
                # field.
                field_tuple = (name, None)
                try:
                    if isinstance(field, str):
                        field_tuple = (name, self.getter(field))
                    else:
                        field_tuple = (name, self.getter(*field))
                except Exception as e:  # Catch all errors intentionally.
                    log.exception(
                        "Error exporting CSV for {name}: {error_class} {error}".format(
                            name=self.__class__.__name__, error_class=e.__class__.__name__, error=e
                        ),
                        stack_info=True,
                    )
                self._fields.append(field_tuple)
        return self._fields

    def getter(self, name, getter=None):
        if not getter:
            method = "field_{0}".format(name)
            return (
                getattr(self, method) if hasattr(self, method) else lambda o: recursive_get(o, name)
            )
        return (lambda o: recursive_get(o, getter)) if isinstance(getter, str) else getter

    def header(self):
        """Generate the CSV header row"""
        return [name for name, getter in self.get_fields()]

    def rows(self):
        """Iterate over queryset objects"""
        return (self.to_row(o) for o in self.queryset)

    def to_row(self, obj):
        """Convert an object into a flat csv row"""
        row = []
        for name, getter in self.get_fields():
            content = ""
            if getter is not None:
                try:
                    content = safestr(getter(obj))
                except Exception as e:  # Catch all errors intentionally.
                    log.exception(
                        "Error exporting CSV for {name}: {error_class} {error}".format(
                            name=self.__class__.__name__, error_class=e.__class__.__name__, error=e
                        ),
                        stack_info=True,
                    )
            row.append(content)
        return row

    def dynamic_fields(self):
        return []


class NestedAdapter(Adapter):
    attribute = None
    nested_fields = None

    def __init__(self, queryset):
        super(NestedAdapter, self).__init__(queryset)
        self._nested_fields = None

    def header(self):
        """Generate the CSV header row"""
        return super(NestedAdapter, self).header() + [
            name for name, getter in self.get_nested_fields()
        ]

    def get_nested_fields(self):
        if not self._nested_fields:
            if not isinstance(self.nested_fields, (list, tuple)):
                raise ValueError("Unsupported nested fields format")
            self._nested_fields = []
            for field in itertools.chain(self.nested_fields, self.nested_dynamic_fields()):
                name = field if isinstance(field, str) else field[0]
                # Retrieving (dynamically) fields is prone to errors,
                # we don't want to break the CSV generation for a unique
                # error so we skip it and introduce a blank to the given
                # field.
                field_tuple = (name, None)
                try:
                    if isinstance(field, str):
                        field_tuple = (name, self.getter(field))
                    else:
                        field_tuple = (name, self.getter(*field))
                except Exception as e:  # Catch all errors intentionally.
                    log.exception(
                        "Error exporting CSV for {name}: {error_class} {error}".format(
                            name=self.__class__.__name__, error_class=e.__class__.__name__, error=e
                        ),
                        stack_info=True,
                    )
                self._nested_fields.append(field_tuple)
        return self._nested_fields

    def get_queryset(self):
        return ((o, n) for o in self.queryset for n in getattr(o, self.attribute))

    def rows(self):
        """Iterate over queryset objects"""
        return (
            self.nested_row(o, n) for o in self.queryset for n in getattr(o, self.attribute, [])
        )

    def nested_row(self, obj, nested):
        """Convert an object into a flat csv row"""
        row = self.to_row(obj)
        for name, getter in self.get_nested_fields():
            content = ""
            if getter is not None:
                try:
                    content = safestr(getter(nested))
                except Exception as e:  # Catch all errors intentionally.
                    log.exception(
                        "Error exporting CSV for {name}: {error_class} {error}".format(
                            name=self.__class__.__name__, error_class=e.__class__.__name__, error=e
                        ),
                        stack_info=True,
                    )
            row.append(content)
        return row

    def nested_dynamic_fields(self):
        return []


def adapter(model):
    """Register an adapter class for a given model"""

    def inner(cls):
        _adapters[model] = cls
        return cls

    return inner


def get_adapter(cls):
    return _adapters.get(cls)


def _metric_getter(key):
    return lambda o: o.get_metrics().get(key, 0)


def metric_fields(cls):
    return [("metric.{0}".format(key), _metric_getter(key)) for key in cls.__metrics_keys__]


def get_writer(out):
    """Get a preconfigured CSV writer for a given output file"""
    return csv.writer(out, quoting=csv.QUOTE_NONNUMERIC, **CONFIG)


def get_reader(infile):
    """Get a preconfigured CSV reader for a given input file"""
    return csv.reader(infile, **CONFIG)


def yield_rows(adapter):
    """Yield a dataset catalog line by line"""
    csvfile = StringIO()
    writer = get_writer(csvfile)
    # Generate header
    writer.writerow(adapter.header())
    yield csvfile.getvalue()
    del csvfile

    for row in adapter.rows():
        csvfile = StringIO()
        writer = get_writer(csvfile)
        writer.writerow(row)
        yield csvfile.getvalue()
        del csvfile


def stream(queryset_or_adapter, basename=None):
    """Stream a csv file from an object list,

    a queryset or an instanciated adapter.
    """
    if isinstance(queryset_or_adapter, Adapter):
        adapter = queryset_or_adapter
    elif isinstance(queryset_or_adapter, (list, tuple)):
        if not queryset_or_adapter:
            raise ValueError("Type detection is not possible with an empty list")
        cls = _adapters.get(queryset_or_adapter[0].__class__)
        adapter = cls(queryset_or_adapter)
    elif isinstance(queryset_or_adapter, db.BaseQuerySet):
        cls = _adapters.get(queryset_or_adapter._document)
        adapter = cls(queryset_or_adapter)
    else:
        raise ValueError(f"Unsupported object type {queryset_or_adapter}")

    timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    headers = {
        "Content-Disposition": "attachment; filename={0}-{1}.csv".format(
            basename or "export", timestamp
        ),
    }
    streamer = stream_with_context(yield_rows(adapter))
    return Response(streamer, mimetype="text/csv", headers=headers)
