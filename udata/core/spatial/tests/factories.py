# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory
from faker.providers import BaseProvider

from udata.tests.factories import unique_string, faker

from ..models import GeoLevel, GeoZone, SpatialCoverage, spatial_granularities


class GeoJsonProvider(BaseProvider):
    '''A Fake GeoJSON provider'''
    def random_range(self, min=1, max=5):
        return range(self.random_int(1, max))

    def coordinates(self):
        return [float(faker.latitude()), float(faker.longitude())]

    def random_coordinates(self):
        return [self.coordinates() for _ in self.random_range()]

    def point(self):
        return {
            'type': 'Point',
            'coordinates': self.coordinates()
        }

    def linestring(self):
        return {
            'type': 'LineString',
            'coordinates': [self.coordinates() for _ in self.random_range()]
        }

    def _polygon(self):
        start = self.coordinates()
        increment = .1 * self.random_digit_not_null()
        return [
            start,
            [start[0], start[1] + increment],
            [start[0] + increment, start[1] + increment],
            [start[0] + increment, start[1]],
            start,
        ]

    def polygon(self):
        return {
            'type': 'Polygon',
            'coordinates': [self._polygon()]
        }

    def multipoint(self):
        return {
            'type': 'MultiPoint',
            'coordinates': [
                self.coordinates() for _ in self.random_range()
            ]
        }

    def multilinestring(self):
        return {
            'type': 'MultiLineString',
            'coordinates': [
                [
                    self.coordinates() for _ in self.random_range()
                ] for _ in self.random_range()
            ]
        }

    def multipolygon(self):
        return {
            'type': 'MultiPolygon',
            'coordinates': [[self._polygon()] for _ in self.random_range(3)]
        }

    def geometry_collection(self):
        element_factories = [
            self.point, self.linestring, self.polygon,
            self.multipoint, self.multilinestring, self.multipolygon
        ]
        return {
            'type': 'GeometryCollection',
            'geometries': [
                self.random_element(element_factories)()
                for _ in self.random_range()
            ]
        }

faker.add_provider(GeoJsonProvider)


def random_spatial_granularity(*args, **kwargs):
    return faker.random_element(
        [row[0] for row in spatial_granularities])


class SpatialCoverageFactory(MongoEngineFactory):
    class Meta:
        model = SpatialCoverage

    geom = factory.LazyAttribute(lambda o: faker.multipolygon())
    granularity = factory.LazyAttribute(random_spatial_granularity)


class GeoZoneFactory(MongoEngineFactory):
    class Meta:
        model = GeoZone

    id = factory.LazyAttribute(lambda o: '/'.join((o.level, o.code)))
    level = factory.LazyAttribute(lambda o: unique_string())
    name = factory.LazyAttribute(lambda o: faker.city())
    code = factory.LazyAttribute(lambda o: faker.postcode())
    geom = factory.LazyAttribute(lambda o: faker.multipolygon())


class GeoLevelFactory(MongoEngineFactory):
    class Meta:
        model = GeoLevel

    id = factory.LazyAttribute(lambda o: unique_string())
    name = factory.LazyAttribute(lambda o: faker.name())
