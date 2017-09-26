# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, timedelta

from flask import url_for

from udata.models import db, WithMetrics, Metrics
from udata.core.metrics import Metric, init_app as init_metrics

from . import APITestCase


class FakeModel(db.Document, WithMetrics):
    name = db.StringField()

    def __unicode__(self):
        return self.name or ''


class FakeModelMetric(Metric):
    name = 'fake-model-metric'
    model = FakeModel
    display_name = 'Fake model metric'

    def get_value(self):
        return 1


class MetricsAPITest(APITestCase):
    def create_app(self):
        app = super(MetricsAPITest, self).create_app()
        app.config['USE_METRICS'] = True
        init_metrics(app)
        return app

    def test_get_metrics_for_model(self):
        '''It should fetch daily metrics for object on GET'''
        obj = FakeModel.objects.create(name='fake')
        metric = FakeModelMetric(obj)
        metric.compute()

        response = self.get(url_for('api.metrics', id=obj.id))

        self.assert200(response)

        data = response.json[0]
        self.assertEqual(data['level'], 'daily')
        self.assertEqual(data['date'], date.today().isoformat())
        self.assertEqual(len(data['values']), 1)
        self.assertEqual(data['values']['fake-model-metric'], 1)

    # def test_get_missing_metric(self):
    #     '''Missing metric should fallback on default value'''
    #     response = self.get(url_for('api.metrics', id='site'))

    #     self.assert200(response)
    #     self.assertEqual(response.json['level'], 'daily')
    #     self.assertEqual(response.json['date'], date.today().isoformat())
    #     self.assertEqual(len(response.json['values']), 1)
    #     self.assertEqual(response.json['values']['fake-site-metric'], 0)

    def test_get_metric_not_found(self):
        '''It should raise a 404 if object does not exists'''
        response = self.get(url_for('api.metrics', id='fake'))

        self.assert404(response)

    def test_get_metrics_for_day(self):
        '''It should fetch daily metrics for a given day'''
        obj = FakeModel.objects.create(name='fake')
        metric = FakeModelMetric(obj)
        metric.compute()
        yesterday = (date.today() - timedelta(1)).isoformat()

        Metrics.objects.update_daily(
            obj, yesterday, metric1='value1', metric2='value2')

        response = self.get(url_for('api.metrics', id=obj.id, day=yesterday))
        self.assert200(response)

        data = response.json[0]
        self.assertEqual(data['level'], 'daily')
        self.assertEqual(data['date'], yesterday)
        self.assertEqual(len(data['values']), 2)
        for i in range(1, 3):
            self.assertEqual(data['values']['metric{0}'.format(i)],
                             'value{0}'.format(i))

    def test_get_metrics_for_day_range(self):
        '''It should fetch daily metrics for a given period'''
        for i in range(5):
            day = (date.today() - timedelta(i)).isoformat()
            Metrics.objects.update_daily('test', day, metric='value')

        period_start = (date.today() - timedelta(3)).isoformat()
        period_end = (date.today() - timedelta(1)).isoformat()

        response = self.get(url_for(
            'api.metrics', id='test', start=period_start, end=period_end))

        self.assert200(response)
        self.assertEqual(len(response.json), 3)
        self.assertEqual(response.json[0]['date'], period_end)
        self.assertEqual(response.json[2]['date'], period_start)
        for metric in response.json:
            self.assertEqual(metric['level'], 'daily')
