# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from udata.factories import ModelFactory

from .models import Transfer


class TransferFactory(ModelFactory):
    class Meta:
        model = Transfer
    comment = factory.Faker('sentence')
