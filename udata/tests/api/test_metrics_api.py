# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, timedelta

from flask import url_for

from udata.models import db, WithMetrics, Metrics
from udata.core.metrics import Metric, init_app as init_metrics

from . import APITestCase


class FakeModel(db.Document, WithMetrics):
    name = db.StringField()


class FakeModelMetric(Metric):
    name = 'fake-model-metric'
    model = FakeModel
    display_name = 'Fake model metric'

    def get_value(self):
        return 1


class MetricsAPITest(APITestCase):
    def create_app(self):
        app = super(MetricsAPITest, self).create_app()
        init_metrics(app)
        return app

    def test_get_metrics_for_model(self):
        '''It should fetch daily metrics for object on GET'''
        obj = FakeModel.objects.create(name='fake')
        metric = FakeModelMetric(obj)
        metric.compute()

        response = self.get(url_for('api.metrics', id=obj.id))

        self.assert200(response)
        self.assertEqual(response.json['level'], 'daily')
        self.assertEqual(response.json['date'], date.today().isoformat())
        self.assertEqual(len(response.json['values']), 1)
        self.assertEqual(response.json['values']['fake-model-metric'], 1)

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
        # FakeSiteMetric.update()
        obj = FakeModel.objects.create(name='fake')
        metric = FakeModelMetric(obj)
        metric.compute()
        yesterday = (date.today() - timedelta(1)).isoformat()

        Metrics.objects.update_daily(obj, yesterday, metric1='value1', metric2='value2')

        response = self.get(url_for('api.metrics_period', id=obj.id, period=yesterday))

        self.assert200(response)
        self.assertEqual(response.json['level'], 'daily')
        self.assertEqual(response.json['date'], yesterday)
        self.assertEqual(len(response.json['values']), 2)
        for i in range(1, 3):
            self.assertEqual(response.json['values']['metric{0}'.format(i)], 'value{0}'.format(i))

    def test_get_metrics_for_day_range(self):
        '''It should fetch my user data on GET'''
        for i in range(5):
            day = (date.today() - timedelta(i)).isoformat()
            Metrics.objects.update_daily('site', day, metric='value')

        period_start = (date.today() - timedelta(3)).isoformat()
        period_end = (date.today() - timedelta(1)).isoformat()
        period = '+'.join([period_start, period_end])

        response = self.get(url_for('api.metrics_period', id='site', period=period))

        self.assert200(response)
        self.assertEqual(len(response.json), 3)
        self.assertEqual(response.json[0]['date'], period_end)
        self.assertEqual(response.json[2]['date'], period_start)
        for metric in response.json:
            self.assertEqual(metric['level'], 'daily')

    # def test_get_single_metric_by_name(self):
    #     '''It should fetch my user data on GET'''
    #     for i in range(5):
    #         day = (date.today() - timedelta(i)).isoformat()
    #         Metrics.objects.update_daily('site', day, metric='value', other='other')

    #     period_start = (date.today() - timedelta(3)).isoformat()
    #     period_end = (date.today() - timedelta(1)).isoformat()
    #     period = ' '.join([period_start, period_end])

    #     response = self.get(url_for('api.metrics_by_name', id='site', period=period, names='metric'))

    #     self.assert200(response)
    #     self.assertEqual(len(response.json), 3)
    #     self.assertEqual(response.json[0]['date'], period_end)
    #     self.assertEqual(response.json[2]['date'], period_start)
    #     for metric in response.json:
    #         self.assertEqual(metric['level'], 'daily')
    #         self.assertEqual(len(metric['values']), 1)
    #         self.assertEqual(metric['values']['metric'], 'value')

    # def test_get_metrics_by_name(self):
    #     '''It should fetch my user data on GET'''
    #     for i in range(5):
    #         day = (date.today() - timedelta(i)).isoformat()
    #         Metrics.objects.update_daily('site', day, metric='value', other='other', fake='fake')

    #     period_start = (date.today() - timedelta(3)).isoformat()
    #     period_end = (date.today() - timedelta(1)).isoformat()
    #     period = ' '.join([period_start, period_end])

    #     response = self.get(url_for('api.metrics_by_name', id='site', period=period, names='metric,fake'))

    #     self.assert200(response)
    #     self.assertEqual(len(response.json), 3)
    #     self.assertEqual(response.json[0]['date'], period_end)
    #     self.assertEqual(response.json[2]['date'], period_start)
    #     for metric in response.json:
    #         self.assertEqual(metric['level'], 'daily')
    #         self.assertEqual(len(metric['values']), 2)
    #         self.assertEqual(metric['values']['metric'], 'value')
    #         self.assertEqual(metric['values']['fake'], 'fake')
