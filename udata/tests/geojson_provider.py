# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from faker.providers import BaseProvider
from geojson.utils import generate_random


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
