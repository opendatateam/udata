# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import mock

from datetime import date, timedelta

from udata.models import db, Metrics, WithMetrics
from udata.core.metrics import Metric
from udata.tests import TestCase, DBTestMixin


class FakeModel(WithMetrics, db.Document):

    def __unicode__(self):
        return ''


class FakeMetric(Metric):
    model = FakeModel
    name = 'fake'

    def get_value(self):
        return 42


class MetricsModelTest(DBTestMixin, TestCase):
    def test_mixin(self):
        obj = FakeModel()
        self.assertIsInstance(obj.metrics, dict)

        obj.save()

        self.assertIn('fake', obj.metrics)
        self.assertEqual(obj.metrics['fake'], 0)

    def build_metrics(self, obj, days=3):
        today = date.today()
        for i in range(days):
            day = (today - timedelta(i)).isoformat()
            Metrics.objects.create(
                object_id=obj.id,
                date=day,
                level='daily',
                values={
                    'metric-1': i,
                    'metric-2': float(i),
                }
            )

    def test_last_for(self):
        obj = FakeModel.objects.create()
        self.build_metrics(obj)

        metrics = Metrics.objects.last_for(obj)
        self.assertIsInstance(metrics, Metrics)
        self.assertEqual(metrics.date, date.today().isoformat())

    def test_get_for(self):
        obj = FakeModel.objects.create()
        self.build_metrics(obj)

        metrics = Metrics.objects.get_for(obj)

        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].date, date.today().isoformat())

    def test_get_for_n_days(self):
        obj = FakeModel.objects.create()
        self.build_metrics(obj, 4)

        metrics = Metrics.objects.get_for(obj, days=3)

        self.assertEqual(len(metrics), 3)

        today = date.today().isoformat()
        first_day = (date.today() - timedelta(2)).isoformat()
        self.assertEqual(metrics[0].date, today)
        self.assertEqual(metrics[2].date, first_day)

    def test_update_daily_create(self):
        obj = FakeModel.objects.create()

        Metrics.objects.update_daily(obj, key='value')

        metrics = Metrics.objects.get(object_id=obj.id)
        self.assertEqual(metrics.values, {'key': 'value'})

    def test_update_daily_update(self):
        obj = FakeModel.objects.create()
        Metrics.objects.create(
            object_id=obj.id,
            level='daily',
            date=date.today().isoformat(),
            values={'key': 'value'}
        )

        Metrics.objects.update_daily(obj, key='new-value')

        metrics = Metrics.objects.get(object_id=obj.id)
        self.assertEqual(metrics.values, {'key': 'new-value'})

    def test_update_daily_add(self):
        obj = FakeModel.objects.create()
        Metrics.objects.create(
            object_id=obj.id,
            level='daily',
            date=date.today().isoformat(),
            values={'key': 'value'}
        )

        Metrics.objects.update_daily(obj, other='new-value')

        metrics = Metrics.objects.get(object_id=obj.id)
        self.assertEqual(metrics.values, {
            'key': 'value',
            'other': 'new-value',
        })


class MetricTest(DBTestMixin, TestCase):
    def setUp(self):
        self.app.config['USE_METRICS'] = True
        self.obj = FakeModel.objects.create()
        self.updated_emitted = False
        self.need_update_emitted = False

    def on_need_update(self, metric):
        self.assertIsInstance(metric, FakeMetric)
        self.assertEqual(metric.target, self.obj)
        self.need_update_emitted = True

    def on_updated(self, metric):
        self.assertIsInstance(metric, FakeMetric)
        self.assertEqual(metric.target, self.obj)
        self.assertIsNotNone(metric.value)
        self.updated_emitted = True

    def test_need_update(self):
        '''It should update the metric on "need_update" signal'''
        metric = FakeMetric(self.obj)

        with FakeMetric.need_update.connected_to(self.on_need_update):
            with FakeMetric.updated.connected_to(self.on_updated):
                metric.trigger_update()

        self.assertTrue(self.need_update_emitted)
        self.assertTrue(self.updated_emitted)

        self.obj.reload()
        self.assertEqual(self.obj.metrics['fake'], 42)

    def test_updated(self):
        '''It should store the updated metric on "updated" signal'''
        metric = FakeMetric(self.obj)
        metric.value = 'some-value'

        with FakeMetric.need_update.connected_to(self.on_need_update):
            with FakeMetric.updated.connected_to(self.on_updated):
                metric.notify_update()

        self.assertFalse(self.need_update_emitted)
        self.assertTrue(self.updated_emitted)

        metrics = Metrics.objects.last_for(self.obj)
        self.assertEqual(metrics.values['fake'], 'some-value')

    @mock.patch('udata.core.metrics.tasks.archive_metric.delay')
    def test_not_archived(self, task):
        '''It should not store the updated metric when archived=False'''
        class NotArchivedMetric(Metric):
            model = FakeModel
            name = 'not-archived'
            archived = False

            def get_value(self):
                return 1024

        metric = NotArchivedMetric(self.obj)

        metric.notify_update()

        self.assertFalse(task.called)

    def test_get_for(self):
        '''All metrics should be registered'''
        self.assertEqual(Metric.get_for(FakeModel), {
            'fake': FakeMetric,
        })
