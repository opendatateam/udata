# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from .models import Dataset, Resource, Checksum, CommunityResource, License


class DatasetFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Dataset

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    frequency = 'unknown'


class VisibleDatasetFactory(DatasetFactory):
    @factory.lazy_attribute
    def resources(self):
        return [ResourceFactory()]


class ChecksumFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Checksum

    type = 'sha1'
    value = factory.Faker('sha1')


class BaseResourceFactory(factory.mongoengine.MongoEngineFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('text')
    filetype = 'file'
    url = factory.Faker('url')
    checksum = factory.SubFactory(ChecksumFactory)
    mime = factory.Faker('mime_type', category='text')
    filesize = factory.Faker('pyint')


class CommunityResourceFactory(BaseResourceFactory):
    class Meta:
        model = CommunityResource


class ResourceFactory(BaseResourceFactory):
    class Meta:
        model = Resource


class LicenseFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = License

    id = factory.Faker('unique_string')
    title = factory.Faker('sentence')
    url = factory.Faker('uri')
