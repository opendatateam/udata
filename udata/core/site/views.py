# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata import search

from udata.i18n import I18nBlueprint
from udata.core.metrics import Metric
from udata.frontend import render, csv
from udata.models import Metrics, Dataset
from udata.utils import multi_to_dict


blueprint = I18nBlueprint('site', __name__)


@blueprint.route('/metrics/')
def metrics():
    metrics = Metrics.objects.last_for('site')
    specs = Metric.get_for('site')
    values = metrics.values if metrics else {}
    return render('metrics.html',
        metrics=dict(
            (key, {'value': values.get(key, spec.default), 'label': spec.display_name})
            for key, spec in specs.items()
        )
    )


@blueprint.route('/datasets.csv')
def datasets_csv():
    params = multi_to_dict(request.args)
    params['facets'] = False
    datasets = search.query(Dataset, **params)
    return csv.stream(datasets.objects, 'datasets')
