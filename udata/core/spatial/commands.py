import json
import logging
import signal
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from textwrap import dedent

import click
import requests
import slugify
from mongoengine import errors
from mongoengine.context_managers import switch_collection

from udata.app import cache
from udata.commands import cli
from udata.core.dataset.models import Dataset
from udata.core.spatial import geoids
from udata.core.spatial.models import GEOZONE_BBOXES_CACHE_KEY, GeoLevel, GeoZone, SpatialCoverage

log = logging.getLogger(__name__)


DEFAULT_GEOZONES_FILE = "https://www.data.gouv.fr/datasets/r/a1bb263a-6cc7-4871-ab4f-2470235a67bf"
DEFAULT_LEVELS_FILE = "https://www.data.gouv.fr/datasets/r/e0206442-78b3-4a00-b71c-c065d20561c8"


@cli.group("spatial")
def grp():
    """Geospatial related operations"""
    pass


def load_levels(col, json_levels):
    for i, level in enumerate(json_levels):
        col.objects(id=level["id"]).modify(
            upsert=True, set__name=level["label"], set__admin_level=level.get("admin_level")
        )
    return i


def load_zones(col, json_geozones):
    loaded_geozones = 0
    for _, geozone in enumerate(json_geozones):
        if geozone.get("is_deleted", False):
            continue
        params = {
            "slug": slugify.slugify(geozone["nom"], separator="-"),
            "level": str(geozone["level"]),
            "code": geozone["codeINSEE"],
            "name": geozone["nom"],
            "uri": geozone["uri"],
        }
        try:
            col.objects(id=geozone["_id"]).modify(
                upsert=True, **{"set__{0}".format(k): v for k, v in params.items()}
            )
            loaded_geozones += 1
        except errors.ValidationError as e:
            log.warning("Validation error (%s) for %s with %s", e, geozone["nom"], params)
            continue
    return loaded_geozones


def load_geozones_bboxes(col, geozones_bboxes):
    loaded = 0
    for zone_id, bbox in geozones_bboxes.items():
        result = col.objects(id=zone_id).update(set__bbox=bbox)
        if result:
            loaded += 1
        else:
            log.warning("No matching GeoZone for id %s: skipped", zone_id)
    return loaded


@contextmanager
def handle_error(to_delete=None):
    """
    Handle errors while loading.
    In case of error, properly log it, remove the temporary files and collections and exit.
    If `to_delete` is given a collection, it will be deleted deleted.
    """
    # Handle keyboard interrupt
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        yield
    except KeyboardInterrupt:
        print("")  # Proper warning message under the "^C" display
        log.warning("Interrupted by signal")
    except Exception as e:
        log.error(e)
    else:
        return  # Nothing to do in case of success
    if to_delete:
        log.info("Removing temporary collection %s", to_delete._get_collection_name())
        to_delete.drop_collection()
    sys.exit(-1)


@grp.command()
@click.argument("geozones-file", default=DEFAULT_GEOZONES_FILE)
@click.argument("levels-file", default=DEFAULT_LEVELS_FILE)
@click.option("-d", "--drop", is_flag=True, help="Drop existing data")
def load(geozones_file, levels_file, drop=False):
    """
    Load a geozones archive from <filename>

    <filename> can be either a local path or a remote URL.
    """
    log.info("Loading GeoZones levels")
    if levels_file.startswith("http"):
        response = requests.get(levels_file)
        # Raise on HTTP errors so a transient error page from the remote server
        # surfaces clearly instead of an opaque JSONDecodeError on the HTML body.
        response.raise_for_status()
        json_levels = response.json()
    else:
        with open(levels_file) as f:
            json_levels = json.load(f)

    ts = datetime.now(UTC).isoformat().replace("-", "").replace(":", "").split(".")[0]
    if drop and GeoLevel.objects.count():
        name = "_".join((GeoLevel._get_collection_name(), ts))
        target = GeoLevel._get_collection_name()
        with switch_collection(GeoLevel, name):
            with handle_error(GeoLevel):
                total = load_levels(GeoLevel, json_levels)
                GeoLevel.objects._collection.rename(target, dropTarget=True)
    else:
        with handle_error():
            total = load_levels(GeoLevel, json_levels)
    log.info("Loaded {total} levels".format(total=total))

    log.info("Loading Zones")
    if geozones_file.startswith("http"):
        response = requests.get(geozones_file)
        response.raise_for_status()
        json_geozones = response.json()
    else:
        with open(geozones_file) as f:
            json_geozones = json.load(f)

    if drop and GeoZone.objects.count():
        name = "_".join((GeoZone._get_collection_name(), ts))
        target = GeoZone._get_collection_name()
        with switch_collection(GeoZone, name):
            with handle_error(GeoZone):
                total = load_zones(GeoZone, json_geozones)
                GeoZone.objects._collection.rename(target, dropTarget=True)
    else:
        with handle_error():
            total = load_zones(GeoZone, json_geozones)
    log.info("Loaded {total} zones".format(total=total))

    log.info("Clean removed geozones in datasets")
    count = fixup_removed_geozone()
    log.info(f"{count} geozones removed from datasets")


@grp.command("load-geozones-bboxes")
@click.argument("geozones-bboxes-file")
def load_geozones_bboxes_command(geozones_bboxes_file):
    """
    Load zone bounding boxes from <geozones-bboxes-file> onto existing GeoZone documents.

    <geozones-bboxes-file> can be either a local path or a remote URL. It's a JSON file:
    a flat object mapping each zone id to its bounding box, e.g.:

    {
        "fr:departement:32": [-0.2821, 43.3108, 1.2032, 44.08],
        "fr:commune:32019": [0.6007, 43.5626, 0.6645, 43.5936]
    }

    Each bounding box is [minx, miny, maxx, maxy] in WGS84 longitude/latitude.
    """
    if geozones_bboxes_file.startswith("http"):
        json_bboxes = requests.get(geozones_bboxes_file).json()
    else:
        with open(geozones_bboxes_file) as f:
            json_bboxes = json.load(f)

    log.info("Loading zone bboxes")
    total = load_geozones_bboxes(GeoZone, json_bboxes)
    log.info("Loaded {total} zone bboxes".format(total=total))

    cache.delete(GEOZONE_BBOXES_CACHE_KEY)


@grp.command()
def migrate():
    """
    Migrate zones from old to new ids in datasets.

    Should only be run once with the new version of geozones w/ geohisto.
    """
    counter = Counter(["zones", "datasets"])
    qs = GeoZone.objects.only("id", "level")
    # Fetch datasets with non-empty spatial zones
    for dataset in Dataset.objects(spatial__zones__gt=[]):
        counter["datasets"] += 1
        new_zones = []
        for current_zone in dataset.spatial.zones:
            counter["zones"] += 1

            level, code = geoids.parse(current_zone.id)
            zone = qs(level=level, code=code).first() or qs(code=code).first()

            if not zone:
                log.warning("No match for %s: skipped", current_zone.id)
                counter["skipped"] += 1
                continue

            new_zones.append(zone.id)
            counter[zone.level] += 1

        # Update dataset with new spatial zones
        dataset.update(
            spatial=SpatialCoverage(granularity=dataset.spatial.granularity, zones=list(new_zones))
        )

    level_summary = "\n".join(
        [
            " - {0}: {1}".format(geolevel.id, counter[geolevel.id])
            for geolevel in GeoLevel.objects.order_by("admin_level")
        ]
    )
    summary = "\n".join(
        [
            dedent(
                """\
    Summary
    =======
    Processed {zones} zones in {datasets} datasets:\
    """.format(**counter)
            ),
            level_summary,
        ]
    )
    log.info(summary)
    log.info("Done")


def fixup_removed_geozone():
    count = 0
    all_datasets = Dataset.objects(spatial__zones__0__exists=True).timeout(False)
    for dataset in all_datasets:
        zones = dataset.spatial.zones
        new_zones = [z for z in zones if getattr(z, "name", None) is not None]

        if len(new_zones) < len(zones):
            log.debug(f"Removing deleted zones from dataset '{dataset.title}'")
            count += len(zones) - len(new_zones)
            dataset.spatial.zones = new_zones
            dataset.save()

    return count
