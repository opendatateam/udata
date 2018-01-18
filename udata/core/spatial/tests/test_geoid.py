# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.tests import TestCase

from .. import geoids
from ..models import GeoZone
from udata.utils import faker


class GeoIDTests(TestCase):
    def test_parse_full_geoid(self):
        geoid = 'level:code@1984-06-07'

        level, code, validity = geoids.parse(geoid)

        self.assertEqual(level, 'level')
        self.assertEqual(code, 'code')
        self.assertEqual(validity, '1984-06-07')

    def test_parse_implicit_latest(self):
        geoid = 'level:code'

        level, code, validity = geoids.parse(geoid)

        self.assertEqual(level, 'level')
        self.assertEqual(code, 'code')
        self.assertEqual(validity, 'latest')

    def test_parse_nested_levels(self):
        geoid = 'nested:level:code@1984-06-07'

        level, code, validity = geoids.parse(geoid)

        self.assertEqual(level, 'nested:level')
        self.assertEqual(code, 'code')
        self.assertEqual(validity, '1984-06-07')

    def test_parse_invalid_geoid(self):
        geoid = 'this-is-not-a-geoid'

        with self.assertRaises(geoids.GeoIDError):
            geoids.parse(geoid)

    def test_build_without_validity(self):
        level = 'level'
        code = 'code'

        geoid = geoids.build(level, code)

        self.assertEqual(geoid, 'level:code')

    def test_build_with_validity_as_string(self):
        level = 'level'
        code = 'code'
        validity = 'latest'

        geoid = geoids.build(level, code, validity)

        self.assertEqual(geoid, 'level:code@latest')

    def test_build_with_validity_as_date(self):
        level = 'level'
        code = 'code'
        validity = faker.past_date()

        geoid = geoids.build(level, code, validity)

        self.assertEqual(geoid, 'level:code@{0:%Y-%m-%d}'.format(validity))

    def test_build_with_validity_as_datetime(self):
        level = 'level'
        code = 'code'
        validity = faker.past_datetime()

        geoid = geoids.build(level, code, validity)

        self.assertEqual(geoid, 'level:code@{0:%Y-%m-%d}'.format(validity))

    def test_build_with_invalid_validity_type(self):
        level = 'level'
        code = 'code'
        validity = object()

        with self.assertRaises(geoids.GeoIDError):
            geoids.build(level, code, validity)

    def test_from_zone_with_validity(self):
        level = 'level'
        code = 'code'
        start = faker.past_date()
        validity = {'start': start, 'end': geoids.END_OF_TIME}
        zone = GeoZone(level=level, code=code, validity=validity)

        geoid = geoids.from_zone(zone)

        self.assertEqual(geoid, 'level:code@{0:%Y-%m-%d}'.format(start))

    def test_from_zone_without_validity(self):
        level = 'level'
        code = 'code'
        zone = GeoZone(level=level, code=code, validity=None)

        geoid = geoids.from_zone(zone)

        self.assertEqual(geoid, 'level:code')
