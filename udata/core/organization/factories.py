# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from .models import Organization, Team


class OrganizationFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Organization

    name = factory.Faker('sentence')
    description = factory.Faker('text')


class TeamFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Team

    name = factory.Faker('sentence')
