# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

import factory

from factory.fuzzy import FuzzyChoice
from factory.mongoengine import MongoEngineFactory
from faker import Faker
from faker.providers import BaseProvider

from udata import models
from udata.core.discussions.models import Message

faker = Faker()


def unique_string(length=None):
    '''Generate unique string'''
    string = str(uuid4())
    return string[:length] if length else string


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


class SiteSettingsFactory(MongoEngineFactory):
    class Meta:
        model = models.SiteSettings


class SiteFactory(MongoEngineFactory):
    class Meta:
        model = models.Site

    id = factory.LazyAttribute(lambda o: faker.word())
    title = factory.LazyAttribute(lambda o: faker.name())
    settings = factory.SubFactory(SiteSettingsFactory)


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


class CommunityResourceFactory(MongoEngineFactory):
    class Meta:
        model = models.CommunityResource

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    url = factory.LazyAttribute(lambda o: faker.url())


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
    @factory.lazy_attribute
    def resources(self):
        return [ResourceFactory()]


class DatasetIssueFactory(MongoEngineFactory):
    class Meta:
        model = models.DatasetIssue

    title = factory.LazyAttribute(lambda o: faker.sentence())


class DatasetDiscussionFactory(MongoEngineFactory):
    class Meta:
        model = models.DatasetDiscussion

    title = factory.LazyAttribute(lambda o: faker.sentence())


class MessageDiscussionFactory(MongoEngineFactory):
    class Meta:
        model = Message

    content = factory.LazyAttribute(lambda o: faker.sentence())


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
    url = factory.LazyAttribute(
        lambda o: '/'.join([faker.url(), unique_string()]))
    type = FuzzyChoice(models.REUSE_TYPES.keys())


class VisibleReuseFactory(ReuseFactory):
    @factory.lazy_attribute
    def datasets(self):
        return [DatasetFactory()]


class LicenseFactory(MongoEngineFactory):
    class Meta:
        model = models.License

    id = factory.Sequence(lambda n: '{0}-{1}'.format(faker.word(), n))
    title = factory.LazyAttribute(lambda o: faker.sentence())


class TopicFactory(MongoEngineFactory):
    class Meta:
        model = models.Topic

    name = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    tags = factory.LazyAttribute(lambda o: [faker.word() for _ in range(3)])

    @factory.lazy_attribute
    def datasets(self):
        return DatasetFactory.create_batch(3)

    @factory.lazy_attribute
    def reuses(self):
        return ReuseFactory.create_batch(3)


class PostFactory(MongoEngineFactory):
    class Meta:
        model = models.Post

    name = factory.LazyAttribute(lambda o: faker.sentence())
    headline = factory.LazyAttribute(lambda o: faker.sentence())
    content = factory.LazyAttribute(lambda o: faker.text())
    private = factory.LazyAttribute(lambda o: False)

    @factory.lazy_attribute
    def datasets(self):
        return DatasetFactory.create_batch(3)

    @factory.lazy_attribute
    def reuses(self):
        return ReuseFactory.create_batch(3)


def random_spatial_granularity(*args, **kwargs):
    return faker.random_element(
        [row[0] for row in models.spatial_granularities])


class SpatialCoverageFactory(MongoEngineFactory):
    class Meta:
        model = models.SpatialCoverage

    geom = factory.LazyAttribute(lambda o: faker.multipolygon())
    granularity = factory.LazyAttribute(random_spatial_granularity)


class TransferFactory(MongoEngineFactory):
    class Meta:
        model = models.Transfer
    comment = factory.LazyAttribute(lambda o: faker.sentence())


class GeoZoneFactory(MongoEngineFactory):
    class Meta:
        model = models.GeoZone

    id = factory.LazyAttribute(lambda o: '/'.join((o.level, o.code)))
    level = factory.LazyAttribute(lambda o: unique_string())
    name = factory.LazyAttribute(lambda o: faker.city())
    code = factory.LazyAttribute(lambda o: faker.postcode())
    geom = factory.LazyAttribute(lambda o: faker.multipolygon())


class GeoLevelFactory(MongoEngineFactory):
    class Meta:
        model = models.GeoLevel

    id = factory.LazyAttribute(lambda o: unique_string())
    name = factory.LazyAttribute(lambda o: faker.name())


def badge_factory(model):
    class BadgeFactory(MongoEngineFactory):
        class Meta:
            model = models.Badge

        kind = FuzzyChoice(model.__badges__.keys())

    return BadgeFactory
