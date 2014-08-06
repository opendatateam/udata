# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import I18nBlueprint
from udata.core.metrics import Metric
from udata.frontend import render, csv
from udata.models import Metrics, Dataset


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
    return csv.stream(Dataset.objects.visible(), 'datasets')
