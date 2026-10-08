import sqlite3

import pytest
from pyproj import CRS

from udata.geopf.client import GeopfError
from udata.geopf.validation import validate_and_detect_srs


def make_gpkg(tmp_path, layers):
    """`layers` is a list of `(table_name, srs_id)`, srs_id being an EPSG code."""
    path = tmp_path / "test.gpkg"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE gpkg_spatial_ref_sys "
        "(srs_id INTEGER PRIMARY KEY, organization TEXT, "
        "organization_coordsys_id INTEGER, definition TEXT)"
    )
    conn.execute("CREATE TABLE gpkg_geometry_columns (table_name TEXT, srs_id INTEGER)")
    for srs_id in {srs_id for _, srs_id in layers}:
        conn.execute(
            "INSERT INTO gpkg_spatial_ref_sys VALUES (?, 'EPSG', ?, ?)",
            (srs_id, srs_id, CRS.from_epsg(srs_id).to_wkt()),
        )
    conn.executemany("INSERT INTO gpkg_geometry_columns VALUES (?, ?)", layers)
    conn.commit()
    conn.close()
    return path.open("rb")


class ValidateAndDetectSrsTest:
    def test_valid_gpkg(self, tmp_path):
        with make_gpkg(tmp_path, [("secteurs_pnc", 4326)]) as f:
            validate_and_detect_srs(f, "gpkg")

    def test_same_srs_across_layers(self, tmp_path):
        with make_gpkg(tmp_path, [("a", 2154), ("b", 2154)]) as f:
            validate_and_detect_srs(f, "gpkg")

    def test_invalid_table_name(self, tmp_path):
        with make_gpkg(tmp_path, [("secteurs-pnc", 4326)]) as f:
            with pytest.raises(GeopfError, match="nom de table invalide : secteurs-pnc"):
                validate_and_detect_srs(f, "gpkg")

    def test_mixed_srs(self, tmp_path):
        with make_gpkg(tmp_path, [("a", 4326), ("b", 2154)]) as f:
            with pytest.raises(GeopfError, match="systèmes de projection"):
                validate_and_detect_srs(f, "gpkg")

    def test_unreadable_gpkg(self, tmp_path):
        path = tmp_path / "bad.gpkg"
        path.write_bytes(b"this is not sqlite")
        with path.open("rb") as f:
            with pytest.raises(GeopfError, match="GeoPackage illisible"):
                validate_and_detect_srs(f, "gpkg")

    def test_unsupported_format(self, tmp_path):
        with make_gpkg(tmp_path, [("a", 4326)]) as f:
            with pytest.raises(GeopfError, match="Unsupported format: csv"):
                validate_and_detect_srs(f, "csv")

    def test_returns_srs(self, tmp_path):
        with make_gpkg(tmp_path, [("a", 2154)]) as f:
            assert validate_and_detect_srs(f, "gpkg") == "EPSG:2154"

    def test_returns_srs_4326(self, tmp_path):
        with make_gpkg(tmp_path, [("a", 4326)]) as f:
            assert validate_and_detect_srs(f, "gpkg") == "EPSG:4326"

    def test_undefined_definition_returns_none(self, tmp_path):
        with make_gpkg(tmp_path, [("a", 4326)]) as f:
            with sqlite3.connect(f.name) as conn:
                conn.execute("UPDATE gpkg_spatial_ref_sys SET definition = 'undefined'")
            assert validate_and_detect_srs(f, "gpkg") is None

    def test_no_geometry_columns_returns_none(self, tmp_path):
        with make_gpkg(tmp_path, []) as f:
            assert validate_and_detect_srs(f, "gpkg") is None
