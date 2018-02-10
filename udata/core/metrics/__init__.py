# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from blinker import Signal
from datetime import date, datetime
from flask import current_app

log = logging.getLogger(__name__)

__all__ = ('Metric', 'MetricMetaClass')

metric_catalog = {}

from udata import entrypoints
from udata.models import db  # noqa: need metrics refactoring

from .tasks import update_metric, archive_metric  # noqa


def update_on_demand(metric):
    update_metric.delay(metric)


def archive_on_updated(metric):
    if metric.archived:
        archive_metric.delay(metric)


class MetricMetaClass(type):
    '''Ensure any child class dispatch the signals'''
    def __new__(cls, name, bases, attrs):

        # Ensure any child class dispatch the signals
        new_class = super(MetricMetaClass, cls).__new__(
            cls, name, bases, attrs)
        if new_class.model and new_class.name:
            new_class.need_update = Signal()
            new_class.need_update.connect(update_on_demand)
            new_class.updated = Signal()
            new_class.updated.connect(archive_on_updated)
            # register the class in the catalog
            if new_class.model not in metric_catalog:
                metric_catalog[new_class.model] = {}
            metric_catalog[new_class.model][new_class.name] = new_class
        return new_class


class Metric(object):
    model = None
    name = None
    display_name = None
    value = None
    default = 0
    value_type = int
    archived = True

    __metaclass__ = MetricMetaClass

    def __init__(self, target, data=None):
        self.target = target
        self.data = data

    @property
    def objects(self):
        return self.model.objects(id=self.target.id)

    def compute(self):
        log.debug('Computing value for %s(%s) metric', self.name, self.target)
        self.value = self.get_value()
        if self.value is not None:
            if isinstance(self.target, db.Document):
                cmd = {'set__metrics__{0}'.format(self.name): self.value}
                self.model.objects(id=self.target.id).update_one(**cmd)
            self.notify_update()

    def store(self):
        from .models import Metrics
        log.debug('Storing metric %s(%s)', self.name, self.target)
        kwargs = {self.name: self.value}
        Metrics.objects.update_daily(self.target, **kwargs)

    def get_value(self):
        '''
        This method encapsulate the metric computing logic

        Implement this method when you inherit this class.
        '''
        raise NotImplementedError

    def aggregate(self, start, end):
        '''
        This method encpsualte the metric aggregation logic.
        Override this method when you inherit this class.
        By default, it takes the last value.
        '''
        last = self.objects(
            level='daily', date__lte=self.iso(end),
            date__gte=self.iso(start)).order_by('-date').first()
        return last.values[self.name]

    def iso(self, value):
        if isinstance(value, basestring):
            return value
        elif isinstance(value, datetime):
            return value.date().isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        else:
            raise ValueError(
                'Unsupported format: {0} ({1})'.format(value, type(value)))

    def trigger_update(self):
        if current_app.config['USE_METRICS']:
            self.need_update.send(self)

    def notify_update(self):
        if current_app.config['USE_METRICS']:
            self.updated.send(self)

    @classmethod
    def aggregate_monthly(cls, queryset, month):
        raise NotImplementedError

    @classmethod
    def get_for(cls, model):
        return metric_catalog.get(model, {})

    @classmethod
    def connect(cls, *signals):
        def callback(sender, **kwargs):
            cls(sender).trigger_update()
        for signal in signals:
            signal.connect(callback, weak=False)


def init_app(app):
    # Load all core metrics
    import udata.core.site.metrics  # noqa
    import udata.core.user.metrics  # noqa
    import udata.core.issues.metrics  # noqa
    import udata.core.discussions.metrics  # noqa
    import udata.core.dataset.metrics  # noqa
    import udata.core.reuse.metrics  # noqa
    import udata.core.organization.metrics  # noqa
    import udata.core.followers.metrics  # noqa

    # Load metrics from plugins
    entrypoints.get_enabled('udata.metrics', app)
