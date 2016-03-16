# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import StringIO

from flask import abort, current_app, request, send_file
import unicodecsv as csv

from udata import theme
from udata.models import Dataset
from udata.i18n import I18nBlueprint
from udata.utils import multi_to_dict
from udata.core.storages import references

blueprint = I18nBlueprint('towns', __name__, url_prefix='/town')


@blueprint.route(
    '/<town:town>/dataset/<dataset:dataset>/resource/<resource_id>/',
    endpoint='town_dataset_resource')
def compute_town_dataset(town, dataset, resource_id):
    """
    Dynamically generate a CSV file about the town from a national one.

    The file targeted by the resource MUST be downloaded within the
    `references` folder with the original name prior to call that view.

    The GET paramaters `town_attr` and `csv_column` are used to
    determine which attribute MUST match the given column of the CSV.
    """
    args = multi_to_dict(request.args)
    if 'town_attr' not in args or 'csv_column' not in args:
        return abort(404)
    if not hasattr(town, args['town_attr']):
        return abort(400)

    for resource in dataset.resources:
        if resource.id == resource_id:
            break

    resource_path = references.path(resource.url.split('/')[-1])
    match = getattr(town, args['town_attr']).encode('utf-8')

    csvfile_out = StringIO.StringIO()
    with open(resource_path, 'rb') as csvfile_in:
        reader = csv.DictReader(csvfile_in, delimiter=str(';'))
        writer = csv.DictWriter(csvfile_out, fieldnames=reader.fieldnames)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for row in reader:
            if row[args['csv_column']].encode('utf-8') == match:
                writer.writerow(row)

    csvfile_out.seek(0)  # Back to 0 otherwise the file is served empty.
    attachment_filename = '{town_name}_{resource_name}.csv'.format(
        town_name=town.name,
        resource_name=resource.title.replace(' ', '_'))
    return send_file(csvfile_out, as_attachment=True,
                     attachment_filename=attachment_filename)


@blueprint.route('/<town:town>/', endpoint='town')
def render_town(town):
    if not current_app.config.get('ACTIVATE_TOWNS'):
        return abort(404)

    from udata.models import TOWN_DATASETS
    town_datasets = [
        town_dataset_class(town)
        for town_dataset_class in TOWN_DATASETS.values()
    ]
    datasets = list(Dataset.objects.visible().filter(spatial__zones=town))
    context = {
        'town': town,
        'town_datasets': town_datasets,
        'datasets': datasets,
    }
    return theme.render('towns/town.html', **context)
