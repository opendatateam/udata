# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory

from udata import models
from udata.utils import faker


class SiteSettingsFactory(MongoEngineFactory):
    class Meta:
        model = models.SiteSettings


class SiteFactory(MongoEngineFactory):
    class Meta:
        model = models.Site

    id = factory.LazyAttribute(lambda o: faker.word())
    title = factory.LazyAttribute(lambda o: faker.name())
    settings = factory.SubFactory(SiteSettingsFactory)
