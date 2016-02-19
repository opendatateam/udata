# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from .. import TestCase, DBTestMixin
from ..factories import (DatasetFactory, UserFactory, GeoZoneFactory,
                         SpatialFactory)


class DatasetModelTest(TestCase, DBTestMixin):
    def test_owned_by_user(self):
        user = UserFactory()
        datasets = [
            DatasetFactory(owner=user, spatial=SpatialFactory(
                zones=[GeoZoneFactory(name='')])),
            DatasetFactory(owner=user, spatial=SpatialFactory()),
        ]

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], dataset)
