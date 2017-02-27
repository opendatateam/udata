# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from .models import Site, SiteSettings


class SiteSettingsFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = SiteSettings


class SiteFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Site

    id = factory.Faker('word')
    title = factory.Faker('name')
    settings = factory.SubFactory(SiteSettingsFactory)
