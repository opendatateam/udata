import re
import sqlite3
from typing import IO

from udata.geopf.client import GeopfError
from udata.geopf.srs import read_gpkg_layers

# Mirrors cartes.gouv.fr's GpkgFormatHandler, which rejects such files before upload
GPKG_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][ A-Za-z0-9_]*$")


def validate_gpkg(f: IO[bytes]) -> str | None:
    """Raise a `GeopfError` with a user-readable reason if geopf would reject the GeoPackage.

    Otherwise return its SRS (e.g. 'EPSG:4326'), None if undetermined.
    """
    try:
        layers = read_gpkg_layers(f)
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
