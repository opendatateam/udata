# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from flask import url_for

from udata.models import db, WithMetrics
from udata.core.site.metrics import SiteMetric

from udata.tests.api import APITestCase


class FakeModel(db.Document, WithMetrics):
    name = db.StringField()


class FakeSiteMetric(SiteMetric):
    name = 'fake-site-metric'
    display_name = 'Fake site metric'
    default = 0

    def get_value(self):
        return 2


class MetricsAPITest(APITestCase):
    def test_get_metrics_for_site(self):
        '''It should fetch my user data on GET'''
        FakeSiteMetric.update()

        response = self.get(url_for('api.metrics', id='site'))

        self.assert200(response)
        self.assertEqual(response.json['level'], 'daily')
        self.assertEqual(response.json['date'], date.today().isoformat())
        self.assertEqual(len(response.json['values']), 1)
        self.assertEqual(response.json['values']['fake-site-metric'], 2)
