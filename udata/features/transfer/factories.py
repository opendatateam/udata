# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from .models import Transfer


class TransferFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Transfer
    comment = factory.Faker('sentence')
