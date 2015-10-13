# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory

from udata.tests.factories import unique_string, faker

from ..models import GeoLevel, GeoZone, SpatialCoverage, spatial_granularities


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
