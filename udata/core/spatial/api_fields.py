from flask import request
from flask_restx import marshal

from udata.api import api, fields
from udata.core.dataset.constants import FULL_OBJECTS_HEADER

GEOM_TYPES = ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon")


geojson = api.model(
    "GeoJSON",
    {
        "type": fields.String(description="The GeoJSON Type", required=True, enum=GEOM_TYPES),
        "coordinates": fields.List(
            fields.Raw(), description="The geometry as coordinates lists", required=True
        ),
    },
)

feature_fields = api.model(
    "GeoJSONFeature",
    {
        "id": fields.String,
        "type": fields.String(required=True, enum=["Feature"]),
        "geometry": fields.Nested(geojson, required=True),
        "properties": fields.Raw,
    },
)

feature_collection_fields = api.model(
    "GeoJSONFeatureCollection",
    {
        "type": fields.String(required=True, enum=["FeatureCollection"]),
        "features": fields.List(fields.Nested(feature_fields), required=True),
    },
)

level_fields = api.model(
    "GeoLevel",
    {
        "id": fields.String(description="The level identifier", required=True),
        "name": fields.String(description="The level name", required=True),
    },
)

zone_fields = api.model(
    "GeoZone",
    {
        "id": fields.String(description="The zone identifier", required=True),
        "name": fields.String(description="The zone name", required=True),
        "slug": fields.String(description="The zone slug", required=True),
        "code": fields.String(description="The zone unique code in the level", required=True),
        "level": fields.String(description="The zone level", required=True),
        "uri": fields.String(description="The zone uri", required=True),
    },
)

granularity_fields = api.model(
    "GeoGranularity",
    {
        "id": fields.String(description="The granularity identifier", required=True),
        "name": fields.String(description="The granularity name", required=True),
    },
)


spatial_coverage_fields = api.model(
    "SpatialCoverage",
    {
        "geom": fields.Nested(
            geojson, allow_null=True, description="A multipolygon for the whole coverage"
        ),
        "zones": fields.Raw(
            attribute=lambda s: marshal(s.zones, zone_fields)
            if request.headers.get(FULL_OBJECTS_HEADER, False, bool)
            else [str(z) for z in s.zones],
            description="The covered zones identifiers (full GeoZone objects if `X-Get-Datasets-Full-Objects` is set, IDs of the zones otherwise)",
        ),
        "granularity": fields.Raw(
            attribute=lambda s: {"id": s.granularity or "other", "name": s.granularity_label}
            if request.headers.get(FULL_OBJECTS_HEADER, False, bool)
            else s.granularity,
            default="other",
            description="The spatial/territorial granularity (full Granularity object if `X-Get-Datasets-Full-Objects` is set, ID of the granularity otherwise)",
        ),
    },
)


zone_suggestion_fields = api.model(
    "TerritorySuggestion",
    {
        "id": fields.String(description="The territory identifier", required=True),
        "name": fields.String(description="The territory name", required=True),
        "code": fields.String(description="The territory main code", required=True),
        "level": fields.String(description="The territory administrative level", required=True),
        "uri": fields.String(description="The zone uri", required=True),
    },
)
