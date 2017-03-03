from __future__ import unicode_literals

import factory

from .models import Issue


class IssueFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Issue

    title = factory.Faker('sentence')
