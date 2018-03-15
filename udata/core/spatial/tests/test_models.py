# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta, date

from udata.tests import TestCase, DBTestMixin
from udata.utils import faker

from ..factories import GeoZoneFactory, GeoLevelFactory
from ..geoids import END_OF_TIME
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
        GeoLevelFactory(id='middle', parents=['top'])
        GeoLevelFactory(id='bottom', parents=['middle'])

        big = GeoZoneFactory(level='top')
        medium = GeoZoneFactory(level='middle', parents=[big.id])
        small = GeoZoneFactory(level='bottom', parents=[big.id, medium.id])

        coverage = SpatialCoverage(zones=[small, medium, big])

        self.assertEqual(coverage.top_label, big.name)


class SpatialTemporalResolutionTest(DBTestMixin, TestCase):
    def test_valid_at_with_validity(self):
        zone = GeoZoneFactory()
        earlier = zone.validity.start - A_YEAR
        later = zone.validity.end + A_YEAR
        GeoZoneFactory(code=zone.code,
                       validity__start=earlier - A_YEAR,
                       validity__end=earlier)
        GeoZoneFactory(code=zone.code,
                       validity__start=later,
                       validity__end=later + A_YEAR)

        valid_at = zone.validity.start + timedelta(1)
        qs = GeoZone.objects(code=zone.code).valid_at(valid_at)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), zone)

    def test_valid_at_without_validity(self):
        zone = GeoZoneFactory(validity=None)
        GeoZoneFactory.create_batch(2)

        qs = GeoZone.objects(code=zone.code).valid_at(date.today())

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), zone)

    def test_valid_at_with_start_validity(self):
        zone = GeoZoneFactory()
        earlier = zone.validity.start - A_YEAR
        later = zone.validity.end + A_YEAR
        GeoZoneFactory(code=zone.code,
                       validity__start=earlier - A_YEAR,
                       validity__end=earlier)
        GeoZoneFactory(code=zone.code,
                       validity__start=later,
                       validity__end=later + A_YEAR)

        valid_at = zone.validity.start
        qs = GeoZone.objects(code=zone.code).valid_at(valid_at)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), zone)

    def test_latest_with_validity(self):
        zone = GeoZoneFactory(validity__end=END_OF_TIME)
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        result = GeoZone.objects(code=zone.code).latest()

        self.assertEqual(result, zone)

    def test_latest_with_validity_ended(self):
        zone = GeoZoneFactory(validity__end=date.today() - timedelta(1))
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        result = GeoZone.objects(code=zone.code).latest()

        self.assertEqual(result, zone)

    def test_latest_without_validity(self):
        zone = GeoZoneFactory(validity=None)
        GeoZoneFactory.create_batch(2, validity=None)

        result = GeoZone.objects(code=zone.code).latest()

        self.assertEqual(result, zone)

    def test_resolve_with_validity_exact_match(self):
        zone = GeoZoneFactory(validity__end=END_OF_TIME)
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        validity = zone.validity.start.isoformat()
        geoid = '{0.level}:{0.code}@{1}'.format(zone, validity)
        result = GeoZone.objects.resolve(geoid)

        self.assertEqual(result, zone)

    def test_resolve_with_validity_match(self):
        zone = GeoZoneFactory(validity__end=END_OF_TIME)
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        validity = faker.date_between(start_date=zone.validity.start,
                                      end_date=zone.validity.end)
        geoid = '{0.level}:{0.code}@{1}'.format(zone, validity.isoformat())
        result = GeoZone.objects.resolve(geoid)

        self.assertEqual(result, zone)

    def test_resolve_with_latest(self):
        zone = GeoZoneFactory(validity__end=END_OF_TIME)
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        geoid = '{0.level}:{0.code}@latest'.format(zone)
        result = GeoZone.objects.resolve(geoid)

        self.assertEqual(result, zone)

    def test_resolve_without_validity(self):
        zone = GeoZoneFactory(validity__end=END_OF_TIME)
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        geoid = '{0.level}:{0.code}'.format(zone)
        result = GeoZone.objects.resolve(geoid)

        self.assertEqual(result, zone)

    def test_resolve_id_only(self):
        zone = GeoZoneFactory(validity__end=END_OF_TIME)
        for i in range(3):
            start = zone.validity.start - (i + 1) * A_YEAR
            end = zone.validity.start - i * A_YEAR
            GeoZoneFactory(code=zone.code,
                           validity__start=start, validity__end=end)

        validity = zone.validity.start.isoformat()
        geoid = '{0.level}:{0.code}@{1}'.format(zone, validity)
        result = GeoZone.objects.resolve(geoid, id_only=True)

        self.assertEqual(result, zone.id)

    def test_resolve_latest_without_validity(self):
        zone = GeoZoneFactory()
        zone.update(unset__validity=True)
        geoid = '{0.level}:{0.code}'.format(zone)
        result = GeoZone.objects.resolve(geoid)

        self.assertEqual(result, zone)
