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

blueprint = I18nBlueprint('territories', __name__)


@blueprint.route(
    '/territory/<territory:territory>/dataset/<dataset:dataset>/resource/<resource_id>/',
    endpoint='territory_dataset_resource')
def compute_territory_dataset(territory, dataset, resource_id):
    """
    Dynamically generate a CSV file about the territory from a national one.

    The file targeted by the resource MUST be downloaded within the
    `references` folder with the original name prior to call that view.

    The GET paramaters `territory_attr` and `csv_column` are used to
    determine which attribute MUST match the given column of the CSV.
    """
    args = multi_to_dict(request.args)
    if 'territory_attr' not in args or 'csv_column' not in args:
        return abort(404)
    if not hasattr(territory, args['territory_attr']):
        return abort(400)

    for resource in dataset.resources:
        if resource.id == resource_id:
            break

    resource_path = references.path(resource.url.split('/')[-1])
    match = getattr(territory, args['territory_attr']).encode('utf-8')

    csvfile_out = StringIO.StringIO()
    with open(resource_path, 'rb') as csvfile_in:
        reader = csv.DictReader(csvfile_in, delimiter=str(';'))
        writer = csv.DictWriter(csvfile_out, fieldnames=reader.fieldnames)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for row in reader:
            if row[args['csv_column']].encode('utf-8') == match:
                writer.writerow(row)

    csvfile_out.seek(0)  # Back to 0 otherwise the file is served empty.
    attachment_filename = '{territory_name}_{resource_name}.csv'.format(
        territory_name=territory.name,
        resource_name=resource.title.replace(' ', '_'))
    return send_file(csvfile_out, as_attachment=True,
                     attachment_filename=attachment_filename)


@blueprint.route('/town/<territory:territory>/', endpoint='territory')
def render_territory(territory):
    if not current_app.config.get('ACTIVATE_TERRITORIES'):
        return abort(404)

    from udata.models import TERRITORY_DATASETS
    territory_dataset_classes = sorted(
        TERRITORY_DATASETS.values(), key=lambda a: a.order)
    territory_datasets = [
        territory_dataset_class(territory)
        for territory_dataset_class in territory_dataset_classes
    ]
    datasets = list(Dataset.objects.visible().filter(spatial__zones=territory))
    context = {
        'territory': territory,
        'territory_datasets': territory_datasets,
        'datasets': datasets,
    }
    return theme.render('territories/territory.html', **context)
