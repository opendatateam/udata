# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.routing import BaseConverter

from udata import models


class LanguagePrefixConverter(BaseConverter):
    regex = r'\w{2}'


class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(super(ListConverter, self).to_url(value) for value in values)


class ModelConverter(BaseConverter):
    model = None

    def to_python(self, value):
        return self.model.objects.get_or_404(slug=value)

    def to_url(self, obj):
        if hasattr(obj, 'slug'):
            return obj.slug
        return obj


class DatasetConverter(ModelConverter):
    model = models.Dataset


class OrganizationConverter(ModelConverter):
    model = models.Organization


class ReuseConverter(ModelConverter):
    model = models.Reuse


class UserConverter(ModelConverter):
    model = models.User


class TopicConverter(ModelConverter):
    model = models.Topic


class PostConverter(ModelConverter):
    model = models.Post


def init_app(app):
    app.url_map.converters['lang'] = LanguagePrefixConverter
    app.url_map.converters['list'] = ListConverter
    app.url_map.converters['dataset'] = DatasetConverter
    app.url_map.converters['org'] = OrganizationConverter
    app.url_map.converters['reuse'] = ReuseConverter
    app.url_map.converters['user'] = UserConverter
    app.url_map.converters['topic'] = TopicConverter
    app.url_map.converters['post'] = PostConverter
