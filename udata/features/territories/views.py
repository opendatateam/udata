# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import StringIO
from collections import namedtuple

import unicodecsv as csv
from flask import abort, current_app, request, send_file, redirect, url_for

from udata import theme
from udata.auth import current_user
from udata.core.storages import references
from udata.core.dataset.permissions import DatasetEditPermission
from udata.i18n import I18nBlueprint
from udata.models import Dataset, GeoZone, TERRITORY_DATASETS
from udata.sitemap import sitemap
from udata.utils import multi_to_dict

blueprint = I18nBlueprint('territories', __name__)


def dict_to_namedtuple(name, data):
    """Convert a `data` dict to a namedtuple.

    Useful for easy attribute access.
    """
    return namedtuple(name, data.keys())(**data)


@blueprint.route(
    ('/territory/<territory:territory>/dataset/<dataset:dataset>'
     '/resource/<resource_id>/'),
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
        if str(resource.id) == str(resource_id):
            break

    resource_path = references.path(resource.url.split('/')[-1])
    match = getattr(territory, args['territory_attr']).encode('utf-8')

    csvfile_out = StringIO.StringIO()
    with open(resource_path, 'rb') as csvfile_in:
        reader = csv.DictReader(csvfile_in, delimiter=str(';'))
        writer = csv.DictWriter(csvfile_out, fieldnames=reader.fieldnames)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for row in reader:
            csv_column = row[args['csv_column']].encode('utf-8')
            # `lstrip` ensure comparison for counties.
            if csv_column.lstrip('0') == match.lstrip('0'):
                writer.writerow(row)

    csvfile_out.seek(0)  # Back to 0 otherwise the file is served empty.
    attachment_filename = '{territory_name}_{resource_name}.csv'.format(
        territory_name=territory.name,
        resource_name=resource.title.replace(' ', '_'))
    return send_file(csvfile_out, as_attachment=True,
                     attachment_filename=attachment_filename)


@blueprint.route('/territory/regions/', endpoint='home')
def render_home():
    if not current_app.config.get('ACTIVATE_TERRITORIES'):
        return abort(404)

    regions = GeoZone.objects.get(id='country/fr').children

    return theme.render('territories/home.html', **{
        'geojson': {
            'type': 'FeatureCollection',
            'features': [region.toGeoJSON() for region in regions]
        }
    })


@blueprint.route('/town/<int:code>/', endpoint='town')
def redirect_town(code):
    """
    Legacy redirect now prefixed with `territories`.
    """
    # Turn the dict into a namedtuple to be consistent in routing.
    territory = dict_to_namedtuple('Territory',
                                   {'code': code, 'level_name': 'town'})
    return redirect(url_for('territories.territory', territory=territory))


@blueprint.route('/territory/<territory:territory>/', endpoint='territory')
def render_territory(territory):
    if not current_app.config.get('ACTIVATE_TERRITORIES'):
        return abort(404)

    DATASETS = TERRITORY_DATASETS[territory.level_name]

    base_dataset_classes = sorted(DATASETS.values(), key=lambda a: a.order)
    base_datasets = [
        base_dataset_class(territory)
        for base_dataset_class in base_dataset_classes
    ]

    # Retrieve all datasets then split between those optionaly owned
    # by an org for that zone and others. We need to know if the current
    # user has datasets for that zone in order to display a custom
    # message to ease the conversion.
    datasets = Dataset.objects.visible().filter(spatial__zones=territory)
    territory_datasets = []
    other_datasets = []
    editable_datasets = []
    if datasets:
        for dataset in datasets:
            if (dataset.organization and
                    territory.id == dataset.organization.zone):
                territory_datasets.append(dataset)
            else:
                other_datasets.append(dataset)
            editable_datasets.append(current_user.is_authenticated and
                                     DatasetEditPermission(dataset).can())
    context = {
        'territory': territory,
        'base_datasets': base_datasets,
        'other_datasets': other_datasets,
        'has_pertinent_datasets': any(editable_datasets),
        'territory_datasets': territory_datasets
    }
    template = 'territories/{level_name}.html'.format(
        level_name=territory.level_name)
    return theme.render(template, **context)


@sitemap.register_generator
def sitemap_urls():
    if current_app.config.get('ACTIVATE_TERRITORIES'):
        for level in current_app.config.get('HANDLED_LEVELS'):
            if level == 'country':
                continue  # Level not fully handled yet.
            for item in GeoZone.objects(level=level).only('code'):
                # Remove 'fr/' manually from the level.
                territory = dict_to_namedtuple(
                    'Territory', {'level_name': level[3:], 'code': item.code})
                yield ('territories.territory', {'territory': territory},
                       None, "weekly", 0.5)
