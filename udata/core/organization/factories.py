# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory

from udata import models
from udata.utils import faker


class OrganizationFactory(MongoEngineFactory):
    class Meta:
        model = models.Organization

    name = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())


class TeamFactory(MongoEngineFactory):
    class Meta:
        model = models.Team

    name = factory.LazyAttribute(lambda o: faker.sentence())
