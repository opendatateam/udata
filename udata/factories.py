# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory


class ModelFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        abstract = True

    @classmethod
    def as_dict(cls, **kwargs):
        return factory.build(dict, FACTORY_CLASS=cls, **kwargs)
