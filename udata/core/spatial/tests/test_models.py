from datetime import timedelta

from udata.tests import TestCase, DBTestMixin

from ..factories import GeoZoneFactory, GeoLevelFactory
from ..models import GeoZone, SpatialCoverage


A_YEAR = timedelta(days=365)


class SpacialCoverageTest(DBTestMixin, TestCase):
    def test_top_label_empty(self):
        coverage = SpatialCoverage()
        self.assertIsNone(coverage.top_label)

    def test_top_label_single(self):
        zone = GeoZoneFactory(name='name', level='level', code='code')
        coverage = SpatialCoverage(zones=[zone])
        self.assertEqual(coverage.top_label, 'name')

    def test_geolabel_priority(self):
        GeoLevelFactory(id='top')
        GeoLevelFactory(id='middle')
        GeoLevelFactory(id='bottom')

        big = GeoZoneFactory(level='top')
        medium = GeoZoneFactory(level='middle')
        small = GeoZoneFactory(level='bottom')

        coverage = SpatialCoverage(zones=[small, medium, big])

        self.assertEqual(coverage.top_label, big.name)


class SpatialTemporalResolutionTest(DBTestMixin, TestCase):

    def test_resolve_id_only(self):
        zone = GeoZoneFactory()
        for i in range(3):
            GeoZoneFactory(code=zone.code)

        geoid = '{0.level}:{0.code}'.format(zone)
        result = GeoZone.objects.resolve(geoid, id_only=True)

        self.assertEqual(result, zone.id)
