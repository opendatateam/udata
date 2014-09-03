# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import SpatialCoverage, TerritoryReference
from udata.core.spatial import register_level
from udata.tests import TestCase


class SpacialCoverageTest(TestCase):
    def test_top_label_empty(self):
        coverage = SpatialCoverage()
        self.assertIsNone(coverage.top_label)

    def test_top_label_single(self):
        territory = TerritoryReference(name='name', level='level', code='code')
        coverage = SpatialCoverage(territories=[territory])
        self.assertEqual(coverage.top_label, 'name')

    def test_geolabel_priority(self):
        register_level('country', 'fake', 'Fake level')

        coverage = SpatialCoverage(territories=[
            TerritoryReference(name='France', level='country', code='fr'),
            TerritoryReference(name='Fake', level='fake', code='fake'),
            TerritoryReference(name='Union Européenne', level='country-group', code='ue'),
        ])

        self.assertEqual(coverage.top_label, 'Union Européenne')
