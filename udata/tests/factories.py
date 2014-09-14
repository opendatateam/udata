# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.fuzzy import FuzzyChoice
from factory.mongoengine import MongoEngineFactory
from faker import Faker
from faker.providers import BaseProvider

from udata import models
from udata.core.spatial import LEVELS

faker = Faker()


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


class SiteFactory(MongoEngineFactory):
    class Meta:
        model = models.Site

    id = factory.LazyAttribute(lambda o: faker.word())
    title = factory.LazyAttribute(lambda o: faker.name())



class UserFactory(MongoEngineFactory):
    class Meta:
        model = models.User

    first_name = factory.LazyAttribute(lambda o: faker.first_name())
    last_name = factory.LazyAttribute(lambda o: faker.last_name())
    email = factory.LazyAttribute(lambda o: faker.email())
    active = True


class AdminFactory(UserFactory):
    @factory.lazy_attribute
    def roles(self):
        admin_role, _ = models.Role.objects.get_or_create(name='admin')
        return [admin_role]


class ResourceFactory(MongoEngineFactory):
    class Meta:
        model = models.Resource

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    url = factory.LazyAttribute(lambda o: faker.url())


class DatasetFactory(MongoEngineFactory):
    class Meta:
        model = models.Dataset

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    frequency = 'unknown'


class VisibleDatasetFactory(DatasetFactory):
    class Meta:
        model = models.Dataset

    @factory.lazy_attribute
    def resources(self):
        return [ResourceFactory()]


class OrganizationFactory(MongoEngineFactory):
    class Meta:
        model = models.Organization

    name = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())


class ReuseFactory(MongoEngineFactory):
    class Meta:
        model = models.Reuse

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    url = factory.LazyAttribute(lambda o: faker.url())
    type = FuzzyChoice(models.REUSE_TYPES.keys())


class LicenseFactory(MongoEngineFactory):
    class Meta:
        model = models.License

    id = factory.LazyAttribute(lambda o: faker.word())
    title = factory.LazyAttribute(lambda o: faker.sentence())


class TopicFactory(MongoEngineFactory):
    class Meta:
        model = models.Topic

    name = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())


class PostFactory(MongoEngineFactory):
    class Meta:
        model = models.Post

    name = factory.LazyAttribute(lambda o: faker.sentence())
    content = factory.LazyAttribute(lambda o: faker.text())


class TerritoryFactory(MongoEngineFactory):
    class Meta:
        model = models.Territory

    level = factory.LazyAttribute(lambda o: faker.random_element(LEVELS.keys()))
    name = factory.LazyAttribute(lambda o: faker.city())
    code = factory.LazyAttribute(lambda o: faker.postcode())
    geom = factory.LazyAttribute(lambda o: faker.multipolygon())


class SpatialCoverageFactory(MongoEngineFactory):
    class Meta:
        model = models.SpatialCoverage

    geom = factory.LazyAttribute(lambda o: faker.multipolygon())
