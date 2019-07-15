# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, datetime
from flask import current_app

from udata.models import db

from . import registry
from .signals import metric_need_update, metric_updated

log = logging.getLogger(__name__)

__all__ = ('Metric', 'MetricMetaClass')


class MetricMetaClass(type):
    '''Ensure any child class dispatches the signals'''
    def __new__(cls, name, bases, attrs):
        # Ensure any child class dispatches the signals
        new_class = super(MetricMetaClass, cls).__new__(
            cls, name, bases, attrs)
        if new_class.model and new_class.name:
            new_class.need_update = metric_need_update
            new_class.updated = metric_updated
            registry.register(new_class)
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

    def __init__(self, target):
        '''Apply these metrics on a given target object instance'''
        self.target = target

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
        This method encapsulates the metric computing logic

        Implement this method when you inherit this class.
        '''
        raise NotImplementedError

    def aggregate(self, start, end):
        '''
        This method encapsulates the metric aggregation logic.
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
        return registry.get_for(model)

    @classmethod
    def connect(cls, *signals):
        def callback(sender, **kwargs):
            cls(sender).trigger_update()
        for signal in signals:
            signal.connect(callback, weak=False)
