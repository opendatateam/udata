# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tests import TestCase

from ..factories import GeoZoneFactory, GeoLevelFactory
from ..models import SpatialCoverage


class SpacialCoverageTest(TestCase):
    def test_top_label_empty(self):
        coverage = SpatialCoverage()
        self.assertIsNone(coverage.top_label)

    def test_top_label_single(self):
        zone = GeoZoneFactory(name='name', level='level', code='code')
        coverage = SpatialCoverage(zones=[zone])
        self.assertEqual(coverage.top_label, 'name')

    def test_geolabel_priority(self):
        GeoLevelFactory(id='top')
        GeoLevelFactory(id='middle', parents=['top'])
        GeoLevelFactory(id='bottom', parents=['middle'])

        big = GeoZoneFactory(level='top')
        medium = GeoZoneFactory(level='middle', parents=[big.id])
        small = GeoZoneFactory(level='bottom', parents=[big.id, medium.id])

        coverage = SpatialCoverage(zones=[small, medium, big])

        self.assertEqual(coverage.top_label, big.name)
