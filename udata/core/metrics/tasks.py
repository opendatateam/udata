import logging

from datetime import date, timedelta

from udata.models import db, Site
from udata.tasks import task, job

from .registry import get_for
from .models import Metrics
from .signals import metric_need_update, metric_updated
from .specs import Metric

log = logging.getLogger(__name__)


@metric_need_update.connect
def update_on_demand(metric):
    update_metric.delay(metric.target.__class__.__name__,
                        str(metric.target.pk),
                        metric.name)


@metric_updated.connect
def archive_on_updated(metric):
    if metric.archived:
        archive_metric.delay(metric.target.__class__.__name__,
                             str(metric.target.pk),
                             metric.name, metric.value)


def _compat(cls, id, name, value=None):
    '''Handle compatibility and deprecation warning on metrics tasks parameters'''
    model = db.resolve_model(cls)
    metrics = get_for(model)
    metric_cls = metrics[name]
    if model is Site:
        metric = metric_cls()
    else:
        obj = model.objects.get(pk=id)
        metric = metric_cls(obj)
    if value is not None:
        metric.value = value
    return metric


@task
def update_metric(classname, id=None, name=None):
    metric = _compat(classname, id, name)
    log.debug('Update metric %s for %s', metric.name, metric.target)
    metric.compute()


@task
def archive_metric(classname, id=None, name=None, value=None):
    metric = _compat(classname, id, name, value)
    log.debug('Store metric %s for %s', metric.name, metric.target)
    metric.store()


@job('bump-metrics')
def bump_metrics(self):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(1)).isoformat()
    log.info('Bumping metrics from to %s to %s', yesterday, today)
    to_bump = Metrics.objects(date=yesterday)

    if to_bump.count() == 0:
        log.info('No metric to bump')
        return

    new_metrics = to_bump.aggregate(
        {'$project': {
            '_id': False,
            'object_id': True,
            'date': {'$literal': today},
            'level': True,
            'values': True,
        }}
    )
    # Use underlying PyMongo insert for bulk insertion from generator
    result = Metrics.objects._collection.insert_many(new_metrics)
    log.info('Processed %s document(s)', len(result.inserted_ids))


def update_metrics_for(obj):
    metrics = Metric.get_for(obj.__class__)
    for metric in metrics.values():
        metric(obj).compute()


def update_site_metrics():
    from udata.models import Site
    metrics = Metric.get_for(Site)
    for metric in metrics.values():
        metric.update()
