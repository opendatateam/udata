# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from udata.core.dataset.factories import DatasetFactory
from udata.core.site.metrics import SiteMetric
from udata.models import db, Metrics, WithMetrics, Site
from udata.tests.helpers import assert_emit

FAKE_VALUE = 42


class FakeModel(WithMetrics, db.Document):
    def __unicode__(self):
        return ''


class FakeSiteMetric(SiteMetric):
    name = 'fake'

    def get_value(self):
        return FAKE_VALUE


@pytest.mark.usefixtures('clean_db')
@pytest.mark.options(USE_METRICS=True)
class SiteMetricTest:
    def test_update(self, app):
        '''It should store the updated metric on "updated" signal'''

        with assert_emit(FakeSiteMetric.need_update, FakeSiteMetric.updated):
            FakeSiteMetric.update()

        metrics = Metrics.objects.last_for(app.config['SITE_ID'])
        assert metrics.values['fake'] == FAKE_VALUE

        site = Site.objects.get(id=app.config['SITE_ID'])
        assert site.metrics['fake'] == FAKE_VALUE

    def test_resources_metric(self, app):
        DatasetFactory.create_batch(3, nb_resources=3)

        site = Site.objects.get(id=app.config['SITE_ID'])
        assert site.metrics['resources'] == 9
