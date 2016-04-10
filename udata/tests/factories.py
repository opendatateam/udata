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
factory.Faker.add_provider(GeoJsonProvider)


def unique_string(length=None):
    '''Generate unique string'''
    string = str(uuid4())
    return string[:length] if length else string


def unique_url():
    '''Generate unique URLs'''
    return '/'.join([faker.url(), unique_string()])


def random_sha1():
    '''Genrate random sha1'''
    return sha1(faker.word()).hexdigest()


class SiteSettingsFactory(MongoEngineFactory):
    class Meta:
        model = models.SiteSettings


class SiteFactory(MongoEngineFactory):
    class Meta:
        model = models.Site

    id = factory.Faker('word')
    title = factory.Faker('name')
    settings = factory.SubFactory(SiteSettingsFactory)


class UserFactory(MongoEngineFactory):
    class Meta:
        model = models.User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
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
    value = factory.LazyAttribute(lambda o: random_sha1())


class BaseResourceFactory(MongoEngineFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('text')
    filetype = 'file'
    url = factory.Faker('url')
    checksum = factory.SubFactory(ChecksumFactory)
    mime = factory.Faker('mime_type', category='text')
    filesize = factory.Faker('pyint')


class CommunityResourceFactory(BaseResourceFactory):
    class Meta:
        model = models.CommunityResource


class ResourceFactory(BaseResourceFactory):
    class Meta:
        model = models.Resource


class DatasetFactory(MongoEngineFactory):
    class Meta:
        model = models.Dataset

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    frequency = 'unknown'


class VisibleDatasetFactory(DatasetFactory):
    @factory.lazy_attribute
    def resources(self):
        return [ResourceFactory()]


class DatasetIssueFactory(MongoEngineFactory):
    class Meta:
        model = models.DatasetIssue

    title = factory.Faker('sentence')


class DatasetDiscussionFactory(MongoEngineFactory):
    class Meta:
        model = models.DatasetDiscussion

    title = factory.Faker('sentence')


class MessageDiscussionFactory(MongoEngineFactory):
    class Meta:
        model = Message

    content = factory.Faker('sentence')


class OrganizationFactory(MongoEngineFactory):
    class Meta:
        model = models.Organization

    name = factory.Faker('sentence')
    description = factory.Faker('text')


class ReuseFactory(MongoEngineFactory):
    class Meta:
        model = models.Reuse

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    url = factory.LazyAttribute(lambda o: unique_url())
    type = FuzzyChoice(models.REUSE_TYPES.keys())


class VisibleReuseFactory(ReuseFactory):
    @factory.lazy_attribute
    def datasets(self):
        return [DatasetFactory()]


class LicenseFactory(MongoEngineFactory):
    class Meta:
        model = models.License

    id = factory.Sequence(lambda n: '{0}-{1}'.format(faker.word(), n))
    title = factory.Faker('sentence')


class TopicFactory(MongoEngineFactory):
    class Meta:
        model = models.Topic

    name = factory.Faker('sentence')
    description = factory.Faker('text')
    tags = factory.LazyAttribute(lambda o: [unique_string() for _ in range(3)])

    @factory.lazy_attribute
    def datasets(self):
        return DatasetFactory.create_batch(3)

    @factory.lazy_attribute
    def reuses(self):
        return ReuseFactory.create_batch(3)


class PostFactory(MongoEngineFactory):
    class Meta:
        model = models.Post

    name = factory.Faker('sentence')
    headline = factory.Faker('sentence')
    content = factory.Faker('text')
    private = False

    @factory.lazy_attribute
    def datasets(self):
        return DatasetFactory.create_batch(3)

    @factory.lazy_attribute
    def reuses(self):
        return ReuseFactory.create_batch(3)


class TransferFactory(MongoEngineFactory):
    class Meta:
        model = models.Transfer
    comment = factory.Faker('sentence')


def badge_factory(model):
    class BadgeFactory(MongoEngineFactory):
        class Meta:
            model = models.Badge

        kind = FuzzyChoice(model.__badges__.keys())

    return BadgeFactory


class GeoZoneFactory(MongoEngineFactory):
    class Meta:
        model = models.GeoZone

    geom = factory.Faker('multipolygon')
