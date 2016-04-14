# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory

from udata import models
from udata.utils import faker


class UserFactory(MongoEngineFactory):
    class Meta:
        model = models.User

    first_name = factory.LazyAttribute(lambda o: faker.first_name())
    last_name = factory.LazyAttribute(lambda o: faker.last_name())
    email = factory.LazyAttribute(lambda o: faker.email())
    active = True


class AdminFactory(UserFactory):
    @factory.lazy_attribute
    def roles(self):
        admin_role, _ = models.Role.objects.get_or_create(name='admin')
        return [admin_role]
