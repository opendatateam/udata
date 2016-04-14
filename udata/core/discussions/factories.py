# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory

from udata import models
from udata.utils import faker


class MessageDiscussionFactory(MongoEngineFactory):
    class Meta:
        model = models.Message

    content = factory.LazyAttribute(lambda o: faker.sentence())
