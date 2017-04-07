# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from faker.providers import BaseProvider

from geojson.utils import generate_random

from udata.utils import add_faker_provider

from .models import GeoLevel, GeoZone, SpatialCoverage, spatial_granularities


class GeoJsonProvider(BaseProvider):
    '''A Fake GeoJSON provider'''
    def random_range(self, min=2, max=5):
        return range(self.random_int(min, max))

    def point(self):
        return generate_random('Point')

    def linestring(self):
        return generate_random('LineString')

    def polygon(self):
        return generate_random('Polygon')

    def multipoint(self):
        coordinates = [
            generate_random('Point')['coordinates']
            for _ in self.random_range()
        ]

        return {
            'type': 'MultiPoint',
            'coordinates': coordinates
        }

    def multilinestring(self):
        coordinates = [
            generate_random('LineString')['coordinates']
            for _ in self.random_range()
        ]

        return {
            'type': 'MultiLineString',
            'coordinates': coordinates
        }

    def multipolygon(self):
        coordinates = [
            generate_random('Polygon')['coordinates']
            for _ in self.random_range()
        ]

        return {
            'type': 'MultiPolygon',
            'coordinates': coordinates
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

    def feature(self):
        element_factories = [
            self.point, self.linestring, self.polygon,
            self.multipoint, self.multilinestring, self.multipolygon
        ]
        return {
            'type': 'Feature',
            'geometry': self.random_element(element_factories)(),
            'properties': {},
        }

    def feature_collection(self):
        return {
            'type': 'FeatureCollection',
            'features': [self.feature() for _ in self.random_range()]
        }


class SpatialProvider(BaseProvider):
    def spatial_granularity(self):
        return self.generator.random_element([
            row[0] for row in spatial_granularities
        ])


add_faker_provider(GeoJsonProvider)
add_faker_provider(SpatialProvider)


class SpatialCoverageFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = SpatialCoverage

    geom = factory.Faker('multipolygon')
    granularity = factory.Faker('spatial_granularity')


class GeoZoneFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = GeoZone

    id = factory.LazyAttribute(lambda o: '/'.join((o.level, o.code)))
    level = factory.Faker('unique_string')
    name = factory.Faker('city')
    code = factory.Faker('zipcode')
    geom = factory.Faker('multipolygon')


class GeoLevelFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = GeoLevel

    id = factory.Faker('unique_string')
    name = factory.Faker('name')
