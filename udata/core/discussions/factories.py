# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from udata.factories import ModelFactory

from .models import Discussion, Message


class DiscussionFactory(ModelFactory):
    class Meta:
        model = Discussion

    title = factory.Faker('sentence')


class MessageDiscussionFactory(ModelFactory):
    class Meta:
        model = Message

    content = factory.Faker('sentence')
