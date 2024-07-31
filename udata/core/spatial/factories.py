import factory
from faker.providers import BaseProvider
from geojson.utils import generate_random

from udata.factories import ModelFactory
from udata.utils import faker_provider

from . import geoids
from .models import GeoLevel, GeoZone, SpatialCoverage, spatial_granularities


@faker_provider
class GeoJsonProvider(BaseProvider):
    """A Fake GeoJSON provider"""

    def random_range(self, min=2, max=5):
        return range(self.random_int(min, max))

    def point(self):
        return generate_random("Point")

    def linestring(self):
        return generate_random("LineString")

    def polygon(self):
        return generate_random("Polygon")

    def multipoint(self):
        coordinates = [generate_random("Point")["coordinates"] for _ in self.random_range()]

        return {"type": "MultiPoint", "coordinates": coordinates}

    def multilinestring(self):
        coordinates = [generate_random("LineString")["coordinates"] for _ in self.random_range()]

        return {"type": "MultiLineString", "coordinates": coordinates}

    def multipolygon(self):
        coordinates = [generate_random("Polygon")["coordinates"] for _ in self.random_range()]

        return {"type": "MultiPolygon", "coordinates": coordinates}

    def geometry_collection(self):
        element_factories = [
            self.point,
            self.linestring,
            self.polygon,
            self.multipoint,
            self.multilinestring,
            self.multipolygon,
        ]
        return {
            "type": "GeometryCollection",
            "geometries": [self.random_element(element_factories)() for _ in self.random_range()],
        }

    def feature(self):
        element_factories = [
            self.point,
            self.linestring,
            self.polygon,
            self.multipoint,
            self.multilinestring,
            self.multipolygon,
        ]
        return {
            "type": "Feature",
            "geometry": self.random_element(element_factories)(),
            "properties": {},
        }

    def feature_collection(self):
        return {
            "type": "FeatureCollection",
            "features": [self.feature() for _ in self.random_range()],
        }


@faker_provider
class SpatialProvider(BaseProvider):
    def spatial_granularity(self):
        return self.generator.random_element([row[0] for row in spatial_granularities])


class GeoZoneFactory(ModelFactory):
    class Meta:
        model = GeoZone

    id = factory.LazyAttribute(geoids.from_zone)
    name = factory.Faker("city")
    slug = factory.Faker("slug")
    code = factory.Faker("zipcode")
    uri = factory.Faker("url")
    level = factory.LazyAttribute(lambda o: GeoLevelFactory().id)


class SpatialCoverageFactory(ModelFactory):
    class Meta:
        model = SpatialCoverage

    zones = factory.LazyAttribute(lambda o: [GeoZoneFactory()])
    granularity = factory.Faker("spatial_granularity")


class GeoLevelFactory(ModelFactory):
    class Meta:
        model = GeoLevel

    id = factory.Faker("unique_string")
    name = factory.Faker("name")
