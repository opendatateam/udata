# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.models import db, Metrics, WithMetrics
from udata.core.site.metrics import SiteMetric
from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import SiteFactory


class FakeModel(WithMetrics, db.Document):
    pass


class FakeSiteMetric(SiteMetric):
    name = 'fake'

    def get_value(self):
        return 'fake-value'


class SiteMetricTest(DBTestMixin, TestCase):
    def setUp(self):
        self.updated_emitted = False
        self.need_update_emitted = False

    def on_need_update(self, metric):
        self.assertIsInstance(metric, FakeSiteMetric)
        self.need_update_emitted = True

    def on_updated(self, metric):
        self.assertIsInstance(metric, FakeSiteMetric)
        self.assertIsNotNone(metric.value)
        self.updated_emitted = True

    def test_update(self):
        '''It should store the updated metric on "updated" signal'''

        with FakeSiteMetric.need_update.connected_to(self.on_need_update):
            with FakeSiteMetric.updated.connected_to(self.on_updated):
                FakeSiteMetric.update()
                # metric.notify_update()

        self.assertTrue(self.need_update_emitted)
        self.assertTrue(self.updated_emitted)

        metrics = Metrics.objects.last_for(self.app.config['SITE_ID'])
        self.assertEqual(metrics.values['fake'], 'fake-value')
