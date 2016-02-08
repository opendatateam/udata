# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from hashlib import sha1
from uuid import uuid4

import factory

from factory.fuzzy import FuzzyChoice
from factory.mongoengine import MongoEngineFactory
from faker import Faker

from udata import models
from udata.core.discussions.models import Message

from .geojson_provider import GeoJsonProvider

faker = Faker()
faker.add_provider(GeoJsonProvider)


def unique_string(length=None):
    '''Generate unique string'''
    string = str(uuid4())
    return string[:length] if length else string


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


class ChecksumFactory(MongoEngineFactory):
    class Meta:
        model = models.Checksum

    type = 'sha1'
    value = factory.LazyAttribute(lambda o: sha1(faker.word()).hexdigest())


class BaseResourceFactory(MongoEngineFactory):
    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    filetype = 'file'
    url = factory.LazyAttribute(lambda o: faker.url())
    checksum = factory.SubFactory(ChecksumFactory)
    mime = factory.LazyAttribute(lambda o: faker.mime_type('text'))
    filesize = factory.LazyAttribute(lambda o: faker.pyint())


class CommunityResourceFactory(BaseResourceFactory):
    class Meta:
        model = models.CommunityResource


class ResourceFactory(BaseResourceFactory):
    class Meta:
        model = models.Resource


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


class TransferFactory(MongoEngineFactory):
    class Meta:
        model = models.Transfer
    comment = factory.LazyAttribute(lambda o: faker.sentence())


def badge_factory(model):
    class BadgeFactory(MongoEngineFactory):
        class Meta:
            model = models.Badge

        kind = FuzzyChoice(model.__badges__.keys())

    return BadgeFactory
