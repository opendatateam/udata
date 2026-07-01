import re

from flask_restx import inputs
from mongoengine.queryset.visitor import Q

from udata.api import API, api
from udata.core.dataset.api_fields import dataset_ref_fields
from udata.core.suggest import normalize, sorted_suggestions
from udata.i18n import _
from udata.models import Dataset

from .api_fields import (
    feature_collection_fields,
    granularity_fields,
    level_fields,
    zone_suggestion_fields,
)
from .constants import (
    DEFAULT_LEVEL_PRIORITY,
    DEFAULT_SUGGEST_LEVELS,
    LEVEL_PRIORITY,
    SUGGESTABLE_LEVELS,
)
from .models import GeoLevel, GeoZone, spatial_granularities

GEOM_TYPES = ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon")
LEGACY_GEOID_PATTERN = r"^([a-z]+:[a-z]+:\d+)@(\d{4}-\d{2}-\d{2})$"


ns = api.namespace("spatial", "Spatial references")


suggest_parser = api.parser()
suggest_parser.add_argument(
    "q",
    type=str,
    help="The string to autocomplete/suggest (empty returns default zones)",
    location="args",
    required=False,
    default="",
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
        """Geospatial zones autocomplete.

        Only well-populated levels are proposed (:data:`SUGGESTABLE_LEVELS`:
        communes, departments, regions, EPCI, ...); detail levels such as
        arrondissements are excluded. Matching is accent-insensitive; results
        are ranked by match quality (exact > prefix > word > substring), then by
        level relevance (:data:`LEVEL_PRIORITY`), so the city of Paris comes
        before its department and the "Grand Paris" intercommunalities, and
        "Val Parisis" (a mere substring) is relegated. An empty query returns
        broad default zones (regions and departments).
        """
        args = suggest_parser.parse_args()
        query = args["q"]
        size = args["size"]

        norm = normalize(query)
        if not norm:
            zones = GeoZone.objects(level__in=DEFAULT_SUGGEST_LEVELS).order_by("name").limit(size)
        else:
            # Candidates are a superset restricted to suggestable levels: match
            # the name (accent-sensitive) and the accent-folded slug (so
            # "orleans" finds "Orléans"), plus raw code/id. Match quality is then
            # refined in Python on the name.
            candidates = GeoZone.objects(
                Q(name__icontains=query)
                | Q(slug__icontains=norm)
                | Q(code__icontains=query)
                | Q(id__icontains=query),
                level__in=SUGGESTABLE_LEVELS,
            )
            zones = sorted_suggestions(
                candidates,
                query,
                get_texts=lambda zone: zone.name,
                secondary=lambda zone: (
                    LEVEL_PRIORITY.get(zone.level, DEFAULT_LEVEL_PRIORITY),
                    zone.name,
                ),
                size=size,
            )

        return [
            {
                "id": zone.id,
                "name": payload_name(zone.name),
                "code": zone.code,
                "level": zone.level,
                "level_name": zone.level_i18n_name,
                "uri": zone.uri,
            }
            for zone in zones
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
