import logging
import re
import sqlite3
from typing import IO

from udata.geopf.client import GeopfError

log = logging.getLogger(__name__)

# Mirrors cartes.gouv.fr's GpkgFormatHandler, which rejects such files before upload
GPKG_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][ A-Za-z0-9_]*$")


def validate_and_detect_srs(f: IO[bytes], file_format: str | None) -> str | None:
    """Raise a `GeopfError` with a user-readable reason if geopf would reject the file.

    Otherwise return its SRS (e.g. 'EPSG:4326'), None if undetermined.
    """
    if (file_format or "").lower() == "gpkg":
        return _validate_gpkg(f)
    raise GeopfError(f"Unsupported format: {file_format}")


def _validate_gpkg(f: IO[bytes]) -> str | None:
    try:
        layers = _read_gpkg_layers(f)
    except sqlite3.Error as e:
        raise GeopfError(f"GeoPackage illisible ({e})") from e

    for table_name, _ in layers:
        if not isinstance(table_name, str) or not GPKG_TABLE_NAME_RE.match(table_name):
            raise GeopfError(f"GeoPackage invalide (nom de table invalide : {table_name})")

    srs = {srs for _, srs in layers if srs}
    if len(srs) > 1:
        raise GeopfError(
            "Ce fichier contient des données dans des systèmes de projection différents"
        )
    return srs.pop() if srs else None


def _read_gpkg_layers(f: IO[bytes]) -> list[tuple[str, str | None]]:
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
