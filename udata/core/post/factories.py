# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory

from udata import models
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.utils import faker


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
