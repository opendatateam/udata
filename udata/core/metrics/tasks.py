# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, timedelta

from udata.tasks import task, job

from .models import Metrics
from .signals import metric_need_update, metric_updated
from .specs import Metric

log = logging.getLogger(__name__)


@metric_need_update.connect
def update_on_demand(metric):
    print('update on demand', metric, metric.target)
    update_metric.delay(metric)


@metric_updated.connect
def archive_on_updated(metric):
    if metric.archived:
        archive_metric.delay(metric)


@task
def update_metric(metric):
    log.debug('Update metric %s for %s', metric.name, metric.target)
    metric.compute()


@task
def archive_metric(metric):
    log.debug('Store metric %s for %s', metric.name, metric.target)
    metric.store()


@job('bump-metrics')
def bump_metrics(self):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(1)).isoformat()
    self.log.info('Bumping metrics from to %s to %s', yesterday, today)
    script = '''
    function() {
        var processed = 0;
        db[collection].find(query).forEach(function(doc) {
            delete doc._id;
            doc.date = options.today;
            db[collection].save(doc);
            processed += 1;
        });
        return processed;
    }
    '''
    processed = Metrics.objects(date=yesterday).exec_js(script, today=today)
    log.info('Processed %s document(s)', processed)


@task
def update_metrics_for(obj):
    metrics = Metric.get_for(obj.__class__)
    for metric in metrics.values():
        metric(obj).compute()


@task
def update_site_metrics():
    from udata.models import Site
    metrics = Metric.get_for(Site)
    for metric in metrics.values():
        metric.update()
