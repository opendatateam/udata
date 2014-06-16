# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from udata import models

faker = Faker()


class UserFactory(MongoEngineFactory):
    FACTORY_FOR = models.User

    first_name = factory.LazyAttribute(lambda o: faker.first_name())
    last_name = factory.LazyAttribute(lambda o: faker.last_name())
    email = factory.LazyAttribute(lambda o: faker.email())


class AdminFactory(UserFactory):
    @factory.lazy_attribute
    def roles(self):
        admin_role, _ = models.Role.objects.get_or_create(name='admin')
        return [admin_role]


class ResourceFactory(MongoEngineFactory):
    FACTORY_FOR = models.Resource

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())


class DatasetFactory(MongoEngineFactory):
    FACTORY_FOR = models.Dataset

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    frequency = 'unknown'


class DatasetWithMetricsFactory(DatasetFactory):
    metrics = factory.LazyAttribute(lambda o: {'followers': 0, 'reuses': 0})


class OrganizationFactory(MongoEngineFactory):
    FACTORY_FOR = models.Organization

    name = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())


class ReuseFactory(MongoEngineFactory):
    FACTORY_FOR = models.Reuse

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    url = factory.LazyAttribute(lambda o: faker.url())
    type = FuzzyChoice(models.REUSE_TYPES.keys())


class ReuseWithMetricsFactory(ReuseFactory):
    metrics = factory.LazyAttribute(lambda o: {'followers': 0, 'datasets': 0})


class LicenseFactory(MongoEngineFactory):
    FACTORY_FOR = models.License

    id = factory.LazyAttribute(lambda o: faker.word())
    title = factory.LazyAttribute(lambda o: faker.sentence())


class TopicFactory(MongoEngineFactory):
    FACTORY_FOR = models.Topic

    name = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())


class PostFactory(MongoEngineFactory):
    FACTORY_FOR = models.Post

    name = factory.LazyAttribute(lambda o: faker.sentence())
    content = factory.LazyAttribute(lambda o: faker.text())
