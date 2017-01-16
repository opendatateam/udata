from __future__ import unicode_literals
from hashlib import sha1

import factory

from factory.mongoengine import MongoEngineFactory

from udata import models
from udata.utils import faker


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


class LicenseFactory(MongoEngineFactory):
    class Meta:
        model = models.License

    id = factory.Sequence(lambda n: '{0}-{1}'.format(faker.word(), n))
    title = factory.LazyAttribute(lambda o: faker.sentence())
