# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from udata import models

faker = Faker()


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
