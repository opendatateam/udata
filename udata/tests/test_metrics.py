# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import date, timedelta

from udata.core.metrics import Metric
from udata.core.metrics.tasks import bump_metrics
from udata.models import db, Metrics, WithMetrics
from udata.tests.helpers import assert_emit, assert_not_emit

pytestmark = pytest.mark.usefixtures('clean_db')


class FakeModel(WithMetrics, db.Document):
    def __unicode__(self):
        return ''


class FakeMetric(Metric):
    model = FakeModel
    name = 'fake'

    def get_value(self):
        return 42


def build_metrics(obj, days=3, today=None):
    today = today or date.today()
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


class MetricsModelTest:
    def test_mixin(self):
        obj = FakeModel()
        assert isinstance(obj.metrics, dict)

        obj.save()

        assert 'fake' in obj.metrics
        assert obj.metrics['fake'] == 0

    def test_last_for(self):
        obj = FakeModel.objects.create()
        build_metrics(obj)

        metrics = Metrics.objects.last_for(obj)
        assert isinstance(metrics, Metrics)
        assert metrics.date == date.today().isoformat()

    def test_get_for(self):
        obj = FakeModel.objects.create()
        build_metrics(obj)

        metrics = Metrics.objects.get_for(obj)

        assert len(metrics) == 1
        assert metrics[0].date == date.today().isoformat()

    def test_get_for_n_days(self):
        obj = FakeModel.objects.create()
        build_metrics(obj, 4)

        metrics = Metrics.objects.get_for(obj, days=3)

        assert len(metrics) == 3

        today = date.today().isoformat()
        first_day = (date.today() - timedelta(2)).isoformat()
        assert metrics[0].date == today
        assert metrics[2].date == first_day

    def test_update_daily_create(self):
        obj = FakeModel.objects.create()

        Metrics.objects.update_daily(obj, key='value')

        metrics = Metrics.objects.get(object_id=obj.id)
        assert metrics.values == {'key': 'value'}

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
        assert metrics.values == {'key': 'new-value'}

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
        assert metrics.values == {
            'key': 'value',
            'other': 'new-value',
        }


@pytest.mark.options(USE_METRICS=True)
class MetricTest:
    def test_need_update(self):
        '''It should update the metric on "need_update" signal'''
        obj = FakeModel.objects.create()
        metric = FakeMetric(obj)

        with assert_emit(FakeMetric.need_update, FakeMetric.updated):
            metric.trigger_update()

        obj.reload()
        assert obj.metrics['fake'] == 42

    def test_updated(self):
        '''It should store the updated metric on "updated" signal'''
        obj = FakeModel.objects.create()
        metric = FakeMetric(obj)
        metric.value = 'some-value'

        with assert_emit(FakeMetric.updated):
            with assert_not_emit(FakeMetric.need_update):
                metric.notify_update()

        metrics = Metrics.objects.last_for(obj)
        assert metrics.values['fake'] == 'some-value'

    def test_not_archived(self, mocker):
        '''It should not store the updated metric when archived=False'''
        task = mocker.patch('udata.core.metrics.tasks.archive_metric.delay')

        class NotArchivedMetric(Metric):
            model = FakeModel
            name = 'not-archived'
            archived = False

            def get_value(self):
                return 1024

        obj = FakeModel.objects.create()
        metric = NotArchivedMetric(obj)

        metric.notify_update()

        assert not task.called

    def test_get_for(self):
        '''All metrics should be registered'''
        metrics = Metric.get_for(FakeModel)
        assert 'fake' in metrics
        assert metrics['fake'] is FakeMetric


@pytest.mark.options(USE_METRICS=True)
class BumpMetricsTest:

    @pytest.fixture
    def today(self, mocker):
        today = date(2019, 4, 20)
        cls = mocker.patch('udata.core.metrics.tasks.date')
        cls.today.return_value = today
        yield today

    def test_no_metrics(self):
        bump_metrics()

        assert Metrics.objects.count() == 0

    def test_bump_all(self, today):
        obj = FakeModel.objects.create()
        days = 3
        build_metrics(obj, days=days, today=(today - timedelta(1)))

        bump_metrics()

        assert len(Metrics.objects.get_for(obj, days=100)) == days + 1
        assert Metrics.objects.last_for(obj).date == today.isoformat()
