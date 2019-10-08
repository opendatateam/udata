# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import date, timedelta

from flask import url_for

from udata.core.metrics import Metric
from udata.models import db, WithMetrics, Metrics
from udata.tests.helpers import assert200, assert404


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


@pytest.mark.usefixtures('clean_db')
@pytest.mark.options(USE_METRICS=True)
class MetricsAPITest:
    modules = []

    def test_get_metrics_for_model(self, api):
        '''It should fetch daily metrics for object on GET'''
        obj = FakeModel.objects.create(name='fake')
        metric = FakeModelMetric(obj)
        metric.compute()

        response = api.get(url_for('api.metrics', id=obj.id))

        assert200(response)

        data = response.json[0]
        assert data['level'] == 'daily'
        assert data['date'] == date.today().isoformat()
        assert len(data['values']) == 1
        assert data['values']['fake-model-metric'] == 1

    def test_get_metric_not_found(self, api):
        '''It should raise a 404 if object does not exists'''
        response = api.get(url_for('api.metrics', id='fake'))

        assert404(response)

    def test_get_metrics_for_day(self, api):
        '''It should fetch daily metrics for a given day'''
        obj = FakeModel.objects.create(name='fake')
        metric = FakeModelMetric(obj)
        metric.compute()
        yesterday = (date.today() - timedelta(1)).isoformat()

        Metrics.objects.update_daily(obj, yesterday,
                                     metric1='value1',
                                     metric2='value2')

        response = api.get(url_for('api.metrics', id=obj.id, day=yesterday))
        assert200(response)

        data = response.json[0]
        assert data['level'] == 'daily'
        assert data['date'] == yesterday
        assert len(data['values']) == 2
        for i in range(1, 3):
            value = data['values']['metric{0}'.format(i)]
            assert value == 'value{0}'.format(i)

    def test_get_metrics_for_day_range(self, api):
        '''It should fetch daily metrics for a given period'''
        for i in range(5):
            day = (date.today() - timedelta(i)).isoformat()
            Metrics.objects.update_daily('test', day, metric='value')

        period_start = (date.today() - timedelta(3)).isoformat()
        period_end = (date.today() - timedelta(1)).isoformat()

        response = api.get(url_for('api.metrics', id='test',
                                   start=period_start, end=period_end))

        assert200(response)
        assert len(response.json) == 3
        assert response.json[0]['date'] == period_end
        assert response.json[2]['date'] == period_start
        for metric in response.json:
            assert metric['level'] == 'daily'
