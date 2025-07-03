from uuid import UUID

from bson import ObjectId
from flask import redirect, request, url_for
from mongoengine.errors import InvalidQueryError, ValidationError
from werkzeug.exceptions import NotFound
from werkzeug.routing import BaseConverter, PathConverter
from werkzeug.urls import url_quote

from udata import models
from udata.core.dataservices.models import Dataservice
from udata.core.spatial.models import GeoZone
from udata.i18n import ISO_639_1_CODES
from udata.mongo import db
from udata.uris import endpoint_for


class LazyRedirect(object):
    """Store location for lazy redirections"""

    def __init__(self, arg):
        self.arg = arg


class LanguagePrefixConverter(BaseConverter):
    def __init__(self, map):
        super(LanguagePrefixConverter, self).__init__(map)
        self.regex = "(?:%s)" % "|".join(ISO_639_1_CODES)


class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split(",")

    def to_url(self, values):
        return ",".join(super(ListConverter, self).to_url(value) for value in values)


class PathListConverter(PathConverter):
    def to_python(self, value):
        return value.split(",")

    def to_url(self, values):
        return ",".join(super(PathListConverter, self).to_url(value) for value in values)


class UUIDConverter(BaseConverter):
    def to_python(self, value):
        try:
            return value if isinstance(value, UUID) else UUID(value.strip())
        except ValueError:
            return NotFound()


class ModelConverter(BaseConverter):
    """
    A base class helper for model helper.

    Allow to give model or slug or ObjectId as parameter to url_for().

    When serializing to url using a model parameter
    it use the slug field if possible and then fallback on the id field.

    When serializing to python, ir try in the following order:

    * fetch by id
    * fetch by slug
    * raise 404
    """

    model = None

    @property
    def has_slug(self):
        return hasattr(self.model, "slug") and isinstance(self.model.slug, db.SlugField)

    @property
    def has_redirected_slug(self):
        return self.has_slug and self.model.slug.follow

    def get_excludes(self):
        return []

    def quote(self, value):
        if self.has_slug:
            return self.model.slug.slugify(value)
        else:
            return url_quote(value)

    def to_python(self, value):
        try:
            return self.model.objects.exclude(*self.get_excludes()).get_or_404(id=value)
        except (NotFound, ValidationError):
            pass
        try:
            quoted = self.quote(value)
            query = db.Q(slug=value) | db.Q(slug=quoted)
            obj = self.model.objects(query).exclude(*self.get_excludes()).get()
        except (InvalidQueryError, self.model.DoesNotExist):
            # If the model doesn't have a slug or matching slug doesn't exist.
            if self.has_redirected_slug:
                latest = self.model.slug.latest(value)
                if latest:
                    return LazyRedirect(latest)
            return NotFound()
        else:
            if obj.slug != value:
                return LazyRedirect(quoted)
        return obj

    def to_url(self, obj):
        if isinstance(obj, str):
            return self.quote(obj)
        elif isinstance(obj, (ObjectId, UUID)):
            return str(obj)
        elif getattr(obj, "slug", None):
            return self.quote(obj.slug)
        elif getattr(obj, "id", None):
            return str(obj.id)
        else:
            raise ValueError('Unable to serialize "%s" to url' % obj)


class DatasetConverter(ModelConverter):
    model = models.Dataset


class DatasetWithoutResourcesConverter(ModelConverter):
    model = models.Dataset

    def get_excludes(self):
        return ["resources"]


class DataserviceConverter(ModelConverter):
    model = Dataservice


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


class ContactPointConverter(ModelConverter):
    model = models.ContactPoint


class ReportConverter(ModelConverter):
    model = models.Report


class TerritoryConverter(PathConverter):
    DEFAULT_PREFIX = "fr"  # TODO: make it a setting parameter

    def to_python(self, value):
        """
        `value` has slashs in it, that's why we inherit from `PathConverter`.

        E.g.: `commune/13200@latest/`, `departement/13@1860-07-01/` or
        `region/76@2016-01-01/Auvergne-Rhone-Alpes/`.

        Note that the slug is not significative but cannot be omitted.
        """
        if "/" not in value:
            return NotFound()

        level, code = value.split("/")[:2]  # Ignore optional slug

        geoid = GeoZone.SEPARATOR.join([level, code])
        zone = GeoZone.objects.resolve(geoid)

        if not zone and GeoZone.SEPARATOR not in level:
            # Try implicit default prefix
            level = GeoZone.SEPARATOR.join([self.DEFAULT_PREFIX, level])
            geoid = GeoZone.SEPARATOR.join([level, code])
            zone = GeoZone.objects.resolve(geoid)

        return zone or NotFound()

    def to_url(self, obj):
        """
        Reconstruct the URL from level name, code or datagouv id and slug.
        """
        level_name = getattr(obj, "level_name", None)
        if not level_name:
            raise ValueError('Unable to serialize "%s" to url' % obj)

        code = getattr(obj, "code", None)
        slug = getattr(obj, "slug", None)
        if code and slug:
            return "{level_name}/{code}/{slug}".format(level_name=level_name, code=code, slug=slug)
        else:
            raise ValueError('Unable to serialize "%s" to url' % obj)


def lazy_raise_or_redirect():
    """
    Raise exception lazily to ensure request.endpoint is set
    Also perform redirect if needed
    """
    if not request.view_args:
        return
    for name, value in request.view_args.items():
        if isinstance(value, NotFound):
            request.routing_exception = value
            break
        elif isinstance(value, LazyRedirect):
            new_args = request.view_args
            new_args[name] = value.arg
            new_url = url_for(request.endpoint, **new_args)
            return redirect(new_url, 308)


def init_app(app):
    app.before_request(lazy_raise_or_redirect)
    app.url_map.converters["lang"] = LanguagePrefixConverter
    app.url_map.converters["list"] = ListConverter
    app.url_map.converters["pathlist"] = PathListConverter
    app.url_map.converters["uuid"] = UUIDConverter
    app.url_map.converters["dataset"] = DatasetConverter
    app.url_map.converters["dataset_without_resources"] = DatasetWithoutResourcesConverter
    app.url_map.converters["dataservice"] = DataserviceConverter
    app.url_map.converters["crid"] = CommunityResourceConverter
    app.url_map.converters["org"] = OrganizationConverter
    app.url_map.converters["reuse"] = ReuseConverter
    app.url_map.converters["user"] = UserConverter
    app.url_map.converters["topic"] = TopicConverter
    app.url_map.converters["post"] = PostConverter
    app.url_map.converters["territory"] = TerritoryConverter
    app.url_map.converters["contact_point"] = ContactPointConverter
    app.url_map.converters["report"] = ReportConverter

    app.jinja_env.globals["endpoint_for"] = endpoint_for
