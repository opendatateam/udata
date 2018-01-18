# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from udata.factories import ModelFactory

from .models import User, Role


class UserFactory(ModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    active = True


class AdminFactory(UserFactory):
    @factory.lazy_attribute
    def roles(self):
        admin_role, _ = Role.objects.get_or_create(name='admin')
        return [admin_role]
