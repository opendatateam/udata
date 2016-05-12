# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory

from udata import models


class DiscussionFactory(MongoEngineFactory):
    class Meta:
        model = models.Discussion

    title = factory.Faker('sentence')


class MessageDiscussionFactory(MongoEngineFactory):
    class Meta:
        model = models.Message

    content = factory.Faker('sentence')
