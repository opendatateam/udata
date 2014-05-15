# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from blinker import Signal

from udata.core import MODULES
from udata.models import db

from .models import Metrics
from .tasks import update_metric, archive_metric

log = logging.getLogger(__name__)

__all__ = ('Metric', 'SiteMetric')

metric_catalog = {}


class MetricMetaClass(type):
    '''Ensure any child class dispatch the signals'''
    def __new__(cls, name, bases, attrs):
        # Ensure any child class dispatch the signals
        new_class = super(MetricMetaClass, cls).__new__(cls, name, bases, attrs)
        if new_class.model and new_class.name:
            new_class.need_update = Signal()
            new_class.need_update.connect(update_metric.delay)
            new_class.updated = Signal()
            new_class.updated.connect(archive_metric.delay)
            # register the class in the catalog
            if not new_class.model in metric_catalog:
                metric_catalog[new_class.model] = {}
            metric_catalog[new_class.model][new_class.name] = new_class
        return new_class


class Metric(object):
    model = None
    name = None
    display_name = None
    value = None
    default = 0

    __metaclass__ = MetricMetaClass

    def __init__(self, target, data=None):
        self.target = target
        self.data = data

    def compute(self):
        log.debug('Computing value for %s(%s) metric', self.name, self.target)
        self.value = self.get_value()
        if isinstance(self.target, db.Document):
            cmd = {'set__metrics__{0}'.format(self.name): self.value}
            self.model.objects(id=self.target.id).update_one(**cmd)
        self.notify_update()

    def store(self):
        log.debug('Storing metric %s(%s)', self.name, self.target)
        kwargs = {self.name: self.value}
        Metrics.objects.update_daily(self.target, **kwargs)

    def get_value(self):
        '''
        This method encapsulate the metric computing logic

        Implement this method when you inherit this class.
        '''
        raise NotImplementedError

    def trigger_update(self):
        self.need_update.send(self)

    def notify_update(self):
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


class SiteMetric(Metric):
    model = 'site'

    def __init__(self, value=None):
        super(SiteMetric, self).__init__('site', value)

    @classmethod
    def update(cls):
        metric = cls()
        metric.trigger_update()

    @classmethod
    def connect(cls, *signals):
        def callback(sender, **kwargs):
            cls.update()
        for signal in signals:
            signal.connect(callback, weak=False)


def init_app(app):
    # Load all core metrics
    for module in MODULES:
        try:
            __import__('udata.core.{0}.metrics'.format(module))
        except ImportError:
            pass
        except Exception as e:
            log.error('Unable to import %s: %s', module, e)

    # Load plugins API
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.metrics'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)
