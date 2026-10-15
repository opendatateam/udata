import io
import sqlite3
import tempfile

from pyproj import CRS

from udata.geopf.srs import detect_srs


def _make_gpkg(epsg: int | None):
    """Create a minimal GPKG SQLite file with one geometry column. Returns an open temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".gpkg")
    with sqlite3.connect(tmp.name) as conn:
        conn.execute(
            "CREATE TABLE gpkg_spatial_ref_sys "
            "(srs_id INTEGER PRIMARY KEY, organization TEXT, "
            "organization_coordsys_id INTEGER, definition TEXT)"
        )
        conn.execute(
            "CREATE TABLE gpkg_geometry_columns "
            "(table_name TEXT, column_name TEXT, geometry_type_name TEXT, srs_id INTEGER)"
        )
        if epsg is not None:
            wkt = CRS.from_epsg(epsg).to_wkt()
            conn.execute(
                "INSERT INTO gpkg_spatial_ref_sys VALUES (?, ?, ?, ?)",
                (epsg, "EPSG", epsg, wkt),
            )
            conn.execute(
                "INSERT INTO gpkg_geometry_columns VALUES (?, ?, ?, ?)",
                ("my_layer", "geom", "POINT", epsg),
            )
    tmp.seek(0)
    return tmp


class DetectSrsGpkgTest:
    def test_epsg4326(self):
        with _make_gpkg(4326) as f:
            assert detect_srs(f, "gpkg") == "EPSG:4326"

    def test_epsg2154(self):
        with _make_gpkg(2154) as f:
            assert detect_srs(f, "gpkg") == "EPSG:2154"

    def test_uppercase_format(self):
        with _make_gpkg(4326) as f:
            assert detect_srs(f, "GPKG") == "EPSG:4326"

    def test_no_geometry_columns(self):
        with _make_gpkg(None) as f:
            assert detect_srs(f, "gpkg") is None

    def test_undefined_definition(self):
        with _make_gpkg(4326) as f:
            with sqlite3.connect(f.name) as conn:
                conn.execute("UPDATE gpkg_spatial_ref_sys SET definition = 'undefined'")
            f.seek(0)
            assert detect_srs(f, "gpkg") is None

    def test_not_a_sqlite_file(self):
        with tempfile.NamedTemporaryFile(suffix=".gpkg") as f:
            f.write(b"this is not sqlite")
            f.seek(0)
            assert detect_srs(f, "gpkg") is None


class DetectSrsOtherFormatsTest:
    def test_csv_returns_none(self):
        assert detect_srs(io.BytesIO(), "csv") is None

    def test_none_format_returns_none(self):
        assert detect_srs(io.BytesIO(), None) is None

    def test_empty_format_returns_none(self):
        assert detect_srs(io.BytesIO(), "") is None
