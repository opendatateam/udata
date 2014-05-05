# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import StringIO
import unicodecsv

from datetime import datetime


from flask import Response

from udata.models import Dataset
from udata.core.metrics import Metric

from udata.core.dataset.views import blueprint as dataset_blueprint
from udata.core.organization.views import blueprint as org_blueprint


def header(specs):
    '''Generate the CSV header row'''
    row = ['id', 'slug', 'title']
    row.extend(('metric.{0}'.format(key) for key in specs.keys()))
    return row


def to_row(dataset, specs):
    '''Convert a dataset into a flat csv row'''
    row = [dataset.id, dataset.slug, dataset.title]
    row.extend((
        dataset.metrics.get(key, spec.default)
        for key, spec in specs.items()
    ))
    return (
        dataset.id,
        dataset.slug,
        dataset.title
    )


def yield_csv_catalog(datasets):
    '''Yield a dataset catalog line by line'''
    csvfile = StringIO.StringIO()
    writer = unicodecsv.writer(csvfile, encoding='utf-8', delimiter=b',', quotechar=b'"')
    # Generate header
    specs = Metric.get_for(Dataset)
    writer.writerow(header(specs))
    yield csvfile.getvalue()

    for dataset in datasets:
        csvfile = StringIO.StringIO()
        writer = unicodecsv.writer(csvfile, encoding='utf-8', delimiter=b',', quotechar=b'"')
        writer.writerow(to_row(dataset, specs))
        yield csvfile.getvalue()


def stream_csv_catalog(datasets):
    '''Stream a csv list of datasets'''
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
    headers = {
        b'Content-Disposition': 'attachment; filename=datasets-{0}.csv'.format(timestamp),
    }
    return Response(yield_csv_catalog(datasets), mimetype="text/csv", headers=headers)


@dataset_blueprint.route('/catalog.csv')
def csv_catalog():
    return stream_csv_catalog(Dataset.objects.visible())


@org_blueprint.route('/<org:org>/catalog.csv', endpoint='csv_catalog')
def org_csv_catalog(org):
    return stream_csv_catalog(Dataset.objects(organization=org).visible())
