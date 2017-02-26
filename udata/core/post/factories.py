# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory

from .models import Post


class PostFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Post

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
