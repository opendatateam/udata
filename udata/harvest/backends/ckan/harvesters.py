import json
import logging
from urllib.parse import urljoin
from uuid import UUID

from udata import uris
from udata.harvest.models import HarvestItem
from udata.i18n import lazy_gettext as _

try:
    from udata.core.dataset.constants import UPDATE_FREQUENCIES
except ImportError:
    # legacy import of constants in udata
    from udata.models import UPDATE_FREQUENCIES
from udata.core.dataset.models import HarvestDatasetMetadata, HarvestResourceMetadata
from udata.core.dataset.rdf import frequency_from_rdf
from udata.frontend.markdown import parse_html
from udata.harvest.backends.base import BaseBackend, HarvestFilter
from udata.harvest.exceptions import HarvestException, HarvestSkipException
from udata.models import GeoZone, License, Resource, SpatialCoverage, db
from udata.utils import daterange_end, daterange_start, get_by

from .schemas.ckan import schema as ckan_schema
from .schemas.dkan import schema as dkan_schema

log = logging.getLogger(__name__)

# dkan is a dummy value for dkan that does not provide resource_type
ALLOWED_RESOURCE_TYPES = ("dkan", "file", "file.upload", "api", "metadata")


class CkanBackend(BaseBackend):
    display_name = "CKAN"
    filters = (
        HarvestFilter(_("Organization"), "organization", str, _("A CKAN Organization name")),
        HarvestFilter(_("Tag"), "tags", str, _("A CKAN tag name")),
    )
    schema = ckan_schema

    def get_headers(self):
        headers = super(CkanBackend, self).get_headers()
        headers["content-type"] = "application/json"
        if self.config.get("apikey"):
            headers["Authorization"] = self.config["apikey"]
        return headers

    def action_url(self, endpoint):
        path = "/".join(["api/3/action", endpoint])
        return urljoin(self.source.url, path)

    def dataset_url(self, name):
        path = "/".join(["dataset", name])
        return urljoin(self.source.url, path)

    def get_action(self, endpoint, fix=False, **kwargs):
        url = self.action_url(endpoint)
        if fix:
            response = self.post(url, "{}", params=kwargs)
        else:
            response = self.get(url, params=kwargs)

        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        mime_type = content_type.split(";", 1)[0]

        if mime_type == "application/json":  # Standard API JSON response
            data = response.json()
            # CKAN API can returns 200 even on errors
            # Only the `success` property allows to detect errors
            if data.get("success", False):
                return data
            else:
                error = data.get("error")
                if isinstance(error, dict):
                    # Error object with message
                    msg = error.get("message", "Unknown error")
                    if "__type" in error:
                        # Typed error
                        msg = ": ".join((error["__type"], msg))
                else:
                    # Error only contains a message
                    msg = error
                raise HarvestException(msg)

        elif mime_type == "text/html":  # Standard html error page
            raise HarvestException("Unknown Error: {} returned HTML".format(url))
        else:
            # If it's not HTML, CKAN respond with raw quoted text
            msg = response.text.strip('"')
            raise HarvestException(msg)

    def get_status(self):
        url = urljoin(self.source.url, "/api/util/status")
        response = self.get(url)
        return response.json()

    def inner_harvest(self):
        """List all datasets for a given ..."""
        fix = False  # Fix should be True for CKAN < '1.8'

        filters = self.config.get("filters", [])
        if len(filters) > 0:
            # Build a q search query based on filters
            # use package_search because package_list doesn't allow filtering
            # use q parameters because fq is broken with multiple filters
            params = []
            for f in filters:
                param = "{key}:{value}".format(**f)
                if f.get("type") == "exclude":
                    param = "-" + param
                params.append(param)
            q = " AND ".join(params)
            # max out rows count to 1000 as per
            # https://docs.ckan.org/en/latest/api/#ckan.logic.action.get.package_search
            response = self.get_action("package_search", fix=fix, q=q, rows=1000)
            names = [r["name"] for r in response["result"]["results"]]
        else:
            response = self.get_action("package_list", fix=fix)
            names = response["result"]

        for name in names:
            # We use `name` as `remote_id` for now, we'll be replace at the beginning of the process
            self.process_dataset(name)
            if self.has_reached_max_items():
                return

    def inner_process_dataset(self, item: HarvestItem):
        response = self.get_action("package_show", id=item.remote_id)

        result = response["result"]
        # DKAN returns a list where CKAN returns an object
        # we "unlist" here instead of after schema validation in order to get the id easily
        if type(result) is list:
            result = result[0]

        # Replace the `remote_id` from `name` to `id`.
        if result.get("id"):
            item.remote_id = result["id"]

        data = self.validate(result, self.schema)

        # Skip if no resource
        if not len(data.get("resources", [])):
            raise HarvestSkipException(f"Dataset {data['name']} has no record")

        dataset = self.get_dataset(item.remote_id)

        if not dataset.harvest:
            dataset.harvest = HarvestDatasetMetadata()

        # Core attributes
        if not dataset.slug:
            dataset.slug = data["name"]
        dataset.title = data["title"]
        dataset.description = parse_html(data["notes"])

        # Detect license
        default_license = dataset.license or License.default()
        dataset.license = License.guess(
            data["license_id"], data["license_title"], default=default_license
        )

        dataset.tags = [t["name"] for t in data["tags"] if t["name"]]

        dataset.harvest.created_at = data["metadata_created"]
        dataset.harvest.modified_at = data["metadata_modified"]

        dataset.harvest.ckan_name = data["name"]

        temporal_start, temporal_end = None, None
        spatial_geom, spatial_zone = None, None

        for extra in data["extras"]:
            key = extra["key"]
            value = extra["value"]
            if value is None or (isinstance(value, str) and not value.strip()):
                # Skip empty extras
                continue
            elif key == "spatial":
                # GeoJSON representation (Polygon or Point)
                spatial_geom = json.loads(value)
            elif key == "spatial-text":
                # Textual representation of the extent / location
                qs = GeoZone.objects(db.Q(name=value) | db.Q(slug=value))
                if qs.count() == 1:
                    spatial_zone = qs.first()
                else:
                    dataset.extras["ckan:spatial-text"] = value
                    log.debug("spatial-text value not handled: %s", value)
            elif key == "spatial-uri":
                # Linked Data URI representing the place name
                dataset.extras["ckan:spatial-uri"] = value
                log.debug("spatial-uri value not handled: %s", value)
            elif key == "frequency":
                # Update frequency
                freq = frequency_from_rdf(value)
                if freq:
                    dataset.frequency = freq
                elif value in UPDATE_FREQUENCIES:
                    dataset.frequency = value
                else:
                    dataset.extras["ckan:frequency"] = value
                    log.debug("frequency value not handled: %s", value)
            # Temporal coverage start
            elif key == "temporal_start":
                temporal_start = daterange_start(value)
            # Temporal coverage end
            elif key == "temporal_end":
                temporal_end = daterange_end(value)
            else:
                dataset.extras[extra["key"]] = value

        if spatial_geom or spatial_zone:
            dataset.spatial = SpatialCoverage()

        if spatial_zone:
            dataset.spatial.zones = [spatial_zone]

        if spatial_geom:
            if spatial_geom["type"] == "Polygon":
                coordinates = [spatial_geom["coordinates"]]
            elif spatial_geom["type"] == "MultiPolygon":
                coordinates = spatial_geom["coordinates"]
            else:
                raise HarvestException("Unsupported spatial geometry")
            dataset.spatial.geom = {"type": "MultiPolygon", "coordinates": coordinates}

        if temporal_start and temporal_end:
            dataset.temporal_coverage = db.DateRange(
                start=temporal_start,
                end=temporal_end,
            )

        # Remote URL
        dataset.harvest.remote_url = self.dataset_url(data["name"])
        if data.get("url"):
            try:
                url = uris.validate(data["url"])
            except uris.ValidationError:
                dataset.harvest.ckan_source = data["url"]
            else:
                # use declared `url` as `remote_url` if any
                dataset.harvest.remote_url = url

        # Resources
        for res in data["resources"]:
            if res["resource_type"] not in ALLOWED_RESOURCE_TYPES:
                continue
            try:
                resource = get_by(dataset.resources, "id", UUID(res["id"]))
            except Exception:
                log.error("Unable to parse resource ID %s", res["id"])
                continue
            if not resource:
                resource = Resource(id=res["id"])
                dataset.resources.append(resource)
            if not resource.harvest:
                resource.harvest = HarvestResourceMetadata()
            resource.title = res.get("name", "") or ""
            resource.description = parse_html(res.get("description"))
            resource.url = res["url"]
            resource.filetype = "remote"
            resource.format = res.get("format")
            resource.mime = res.get("mimetype")
            resource.hash = res.get("hash")
            resource.harvest.created_at = res["created"]
            resource.harvest.modified_at = res["last_modified"]

        return dataset


class DkanBackend(CkanBackend):
    schema = dkan_schema
    filters = []
