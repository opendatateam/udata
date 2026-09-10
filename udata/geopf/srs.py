import logging
import sqlite3
from typing import IO

log = logging.getLogger(__name__)

DEFAULT_SRS = "EPSG:4326"


def detect_srs(f: IO[bytes], file_format: str | None) -> str | None:
    """Return SRS string (e.g. 'EPSG:4326') or None if undetermined.

    Currently supports GeoPackage. Shapefile (.prj + pyproj) and spec-defined
    WGS84 formats (GeoJSON, KML, KMZ, GPX) can be added here without changing
    the pipeline.
    """
    fmt = (file_format or "").lower()
    if fmt == "gpkg":
        return _from_gpkg(f)
    return None


def _from_gpkg(f: IO[bytes]) -> str | None:
    # Lazy import: pyproj uses PROJ which is not fork-safe. Importing here
    # ensures PROJ is only initialized after the fork, inside the worker process.
    from pyproj import CRS

    try:
        with sqlite3.connect(f.name) as conn:
            row = conn.execute("SELECT srs_id FROM gpkg_geometry_columns LIMIT 1").fetchone()
            if row is None:
                return None
            wkt_row = conn.execute(
                "SELECT definition FROM gpkg_spatial_ref_sys WHERE srs_id = ?",
                (row[0],),
            ).fetchone()
            if wkt_row and wkt_row[0] and wkt_row[0] != "undefined":
                auth = CRS.from_wkt(wkt_row[0]).to_authority()
                if auth:
                    return f"{auth[0]}:{auth[1]}"
    except Exception:
        log.warning("geopf: failed to detect SRS from GPKG", exc_info=True)
    return None
