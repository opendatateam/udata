from udata.api import api, fields, geojson

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

granularity_fields = api.model(
    "GeoGranularity",
    {
        "id": fields.String(description="The granularity identifier", required=True),
        "name": fields.String(description="The granularity name", required=True),
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
