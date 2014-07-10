# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import I18nBlueprint
from udata.core.metrics import Metric
from udata.frontend import render
from udata.models import Metrics


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
    # return render('metrics.html',
    #     metrics=dict(
    #         (key, {'value': value, 'label': specs[key].display_name})
    #         for key, value in values.items()
    #     )
    # )
