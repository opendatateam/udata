# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from .models import Discussion, Message


class DiscussionFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Discussion

    title = factory.Faker('sentence')


class MessageDiscussionFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Message

    content = factory.Faker('sentence')
