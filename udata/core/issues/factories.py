from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory

from .models import Issue


class IssueFactory(MongoEngineFactory):
    class Meta:
        model = Issue

    title = factory.Faker('sentence')
