import logging
import sqlite3
from typing import IO

log = logging.getLogger(__name__)

DEFAULT_SRS = "EPSG:4326"


def read_gpkg_layers(f: IO[bytes]) -> list[tuple[str, str | None]]:
    """Return `(table_name, srs)` for each geometry layer, `srs` being None if undetermined.

    Raises `sqlite3.Error` if the file is not a readable GeoPackage.
    """
    # Lazy import: pyproj uses PROJ which is not fork-safe. Importing here
    # ensures PROJ is only initialized after the fork, inside the worker process.
    from pyproj import CRS

    with sqlite3.connect(f.name) as conn:
        rows = conn.execute(
            "SELECT gc.table_name, rs.definition FROM gpkg_geometry_columns gc "
            "LEFT JOIN gpkg_spatial_ref_sys rs ON gc.srs_id = rs.srs_id"
        ).fetchall()

    layers = []
    for table_name, definition in rows:
        srs = None
        if definition and definition != "undefined":
            try:
                auth = CRS.from_wkt(definition).to_authority()
            except Exception:
                log.warning("geopf: failed to parse GPKG SRS definition", exc_info=True)
            else:
                srs = f"{auth[0]}:{auth[1]}" if auth else None
        layers.append((table_name, srs))
    return layers
