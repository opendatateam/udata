import re

from flask_restx import inputs
from mongoengine.queryset.visitor import Q

from udata.api import API, api
from udata.core.dataset.api_fields import dataset_ref_fields
from udata.i18n import _
from udata.models import Dataset

from .api_fields import (
    feature_collection_fields,
    granularity_fields,
    level_fields,
    zone_suggestion_fields,
)
from .models import GeoLevel, GeoZone, spatial_granularities

GEOM_TYPES = ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon")
LEGACY_GEOID_PATTERN = r"^([a-z]+:[a-z]+:\d+)@(\d{4}-\d{2}-\d{2})$"


ns = api.namespace("spatial", "Spatial references")


suggest_parser = api.parser()
suggest_parser.add_argument(
    "q", type=str, help="The string to autocomplete/suggest", location="args", required=True
)
suggest_parser.add_argument(
    "size", type=int, help="The amount of suggestion to fetch", location="args", default=10
)


def payload_name(name):
    """localize name"""
    return _(name)  # Avoid dict quotes in gettext


def legacy_geoid(legacy_id):
    """Returns an geoid without validity date
    as we do not support it anymore"""
    match = re.match(LEGACY_GEOID_PATTERN, legacy_id)
    if match:
        return legacy_id.split("@")[0]
    return legacy_id


@ns.route("/zones/suggest/", endpoint="suggest_zones")
class SuggestZonesAPI(API):
    @api.marshal_list_with(zone_suggestion_fields)
    @api.expect(suggest_parser)
    @api.doc("suggest_zones")
    def get(self):
        """Geospatial zones suggest endpoint using mongoDB contains"""
        args = suggest_parser.parse_args()
        geozones = GeoZone.objects(
            Q(name__icontains=args["q"]) | Q(code__icontains=args["q"]) | Q(id__icontains=args["q"])
        )

        # We're manually sorting based on zone level int (cause we don't have the int value directly in mongo document)
        level_id_to_int_level = {level.id: level.admin_level for level in GeoLevel.objects()}
        geozones = sorted(geozones, key=lambda zone: level_id_to_int_level[zone.level])

        return [
            {
                "id": geozone.id,
                "name": payload_name(geozone.name),
                "code": geozone.code,
                "level": geozone.level,
                "uri": geozone.uri,
            }
            for geozone in geozones[: args["size"]]
        ]


dataset_parser = api.parser()
dataset_parser.add_argument(
    "dynamic", type=inputs.boolean, help="Append dynamic datasets", location="args", required=False
)
dataset_parser.add_argument(
    "size", type=int, help="The amount of datasets to fetch", location="args", default=25
)


@ns.route("/zones/<list:ids>/", endpoint="zones")
class ZonesAPI(API):
    @api.doc("spatial_zones", params={"ids": "A zone identifiers list (comma separated)"})
    @api.marshal_with(feature_collection_fields)
    def get(self, ids):
        """Fetch a zone list as GeoJSON"""
        ids_list = list(map(legacy_geoid, ids))
        zones = GeoZone.objects.in_bulk(ids_list)
        zones = [zones[id] for id in ids_list]
        return {
            "type": "FeatureCollection",
            "features": [z.toGeoJSON() for z in zones],
        }


@ns.route("/zone/<id>/datasets/", endpoint="zone_datasets")
class ZoneDatasetsAPI(API):
    @api.doc("spatial_zone_datasets", params={"id": "A zone identifier"})
    @api.expect(dataset_parser)
    @api.marshal_with(dataset_ref_fields)
    def get(self, id):
        """Fetch datasets for a given zone"""
        id = legacy_geoid(id)
        args = dataset_parser.parse_args()
        zone = GeoZone.objects.get_or_404(id=id)
        datasets = []
        datasets += list(Dataset.objects.visible().filter(spatial__zones=zone).limit(args["size"]))
        return datasets


@ns.route("/zone/<id>/", endpoint="zone")
class ZoneAPI(API):
    @api.doc("spatial_zone", params={"id": "A zone identifier"})
    def get(self, id):
        """Fetch a zone"""
        id = legacy_geoid(id)
        zone = GeoZone.objects.get_or_404(id=id)
        return zone.toGeoJSON()


@ns.route("/levels/", endpoint="spatial_levels")
class SpatialLevelsAPI(API):
    @api.doc("spatial_levels")
    @api.marshal_list_with(level_fields)
    def get(self):
        """List all known levels"""
        return [{"id": level.id, "name": _(level.name)} for level in GeoLevel.objects]


@ns.route("/granularities/", endpoint="spatial_granularities")
class SpatialGranularitiesAPI(API):
    @api.doc("spatial_granularities")
    @api.marshal_list_with(granularity_fields)
    def get(self):
        """List all known spatial granularities"""
        return [
            {
                "id": id,
                "name": name,
            }
            for id, name in spatial_granularities
        ]


@ns.route("/coverage/<level>/", endpoint="spatial_coverage")
class SpatialCoverageAPI(API):
    @api.doc("spatial_coverage")
    @api.marshal_list_with(feature_collection_fields)
    def get(self, level):
        """List each zone for a given level with their datasets count"""
        level = GeoLevel.objects.get_or_404(id=level)
        features = []

        for zone in GeoZone.objects(level=level.id):
            features.append(
                {
                    "id": zone.id,
                    "type": "Feature",
                    "properties": {
                        "name": _(zone.name),
                        "code": zone.code,
                        "uri": zone.uri,
                        "datasets": zone.metrics.get("datasets", 0),
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}
