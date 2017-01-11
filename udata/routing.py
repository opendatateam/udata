# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId
from uuid import UUID

from flask import request
from mongoengine.errors import InvalidQueryError
from werkzeug.routing import BaseConverter, NotFound, PathConverter

from udata import models
from udata.i18n import ISO_639_1_CODES


class LanguagePrefixConverter(BaseConverter):
    def __init__(self, map):
        super(LanguagePrefixConverter, self).__init__(map)
        self.regex = '(?:%s)' % '|'.join(ISO_639_1_CODES)


class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(super(ListConverter, self).to_url(value)
                        for value in values)


class PathListConverter(PathConverter):
    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(super(PathListConverter, self).to_url(value)
                        for value in values)


class UUIDConverter(BaseConverter):
    def to_python(self, value):
        return value if isinstance(value, UUID) else UUID(value)


class ModelConverter(BaseConverter):
    '''
    A base class helper for model helper.

    Allow to give model or slug or ObjectId as parameter to url_for().

    When serializing to url using a model parameter
    it use the slug field if possible and then fallback on the id field.

    When serializing to python, ir try in the following order:

    * fetch by slug
    * fetch by id
    * raise 404
    '''

    model = None

    def to_python(self, value):
        try:
            obj = self.model.objects(slug=value).first()
        except InvalidQueryError:  # If the model doesn't have a slug.
            obj = None
        try:
            return obj or self.model.objects.get_or_404(id=value)
        except NotFound as e:
            return e

    def to_url(self, obj):
        if isinstance(obj, (basestring, ObjectId, UUID)):
            return str(obj)
        elif getattr(obj, 'slug', None):
            return obj.slug
        elif getattr(obj, 'id', None):
            return str(obj.id)
        else:
            raise ValueError('Unable to serialize "%s" to url' % obj)


class DatasetConverter(ModelConverter):
    model = models.Dataset


class CommunityResourceConverter(ModelConverter):
    model = models.CommunityResource


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


class TerritoryConverter(ModelConverter, PathConverter):
    model = models.GeoZone

    def to_python(self, value):
        """
        `value` has a slash in it, that's why we inherit from `PathConverter`.

        E.g.: `town/13200`, `county/13 or `region/93`.
        """
        if '/' not in value:
            return

        level, code = value.split('/')
        return self.model.objects.get_or_404(
            code=code, level='fr/{level}'.format(level=level))

    def to_url(self, obj):
        """Reconstruct the URL with slash from level name and code."""
        level_name = getattr(obj, 'level_name', None)
        code = getattr(obj, 'code', None)
        if level_name and code:
            return '{level_name}/{code}'.format(
                level_name=level_name, code=code)
        else:
            raise ValueError('Unable to serialize "%s" to url' % obj)


def lazy_raise_404():
    '''Raise 404 lazily to ensure request.endpoint is set'''
    if not request.view_args:
        return
    for arg in request.view_args.values():
        if isinstance(arg, NotFound):
            request.routing_exception = arg
            break


def init_app(app):
    app.before_request(lazy_raise_404)
    app.url_map.converters['lang'] = LanguagePrefixConverter
    app.url_map.converters['list'] = ListConverter
    app.url_map.converters['pathlist'] = PathListConverter
    app.url_map.converters['uuid'] = UUIDConverter
    app.url_map.converters['dataset'] = DatasetConverter
    app.url_map.converters['crid'] = CommunityResourceConverter
    app.url_map.converters['org'] = OrganizationConverter
    app.url_map.converters['reuse'] = ReuseConverter
    app.url_map.converters['user'] = UserConverter
    app.url_map.converters['topic'] = TopicConverter
    app.url_map.converters['post'] = PostConverter
    app.url_map.converters['territory'] = TerritoryConverter
