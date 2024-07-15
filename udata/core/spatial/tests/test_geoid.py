import pytest

from .. import geoids
from ..models import GeoZone


class GeoIDTest:
    def test_parse_full_geoid(self):
        geoid = 'level:code'

        level, code = geoids.parse(geoid)

        assert level == 'level'
        assert code == 'code'

    def test_parse_legacy_geoid(self):
        geoid = 'level/code'

        level, code = geoids.parse(geoid)

        assert level == 'level'
        assert code == 'code'

    def test_parse_implicit_latest(self):
        geoid = 'level:code'

        level, code = geoids.parse(geoid)

        assert level == 'level'
        assert code == 'code'

    def test_parse_nested_levels(self):
        geoid = 'nested:level:code'

        level, code = geoids.parse(geoid)

        assert level == 'nested:level'
        assert code == 'code'

    def test_parse_country_subset_levels(self):
        geoid = 'country-subset:country:code'

        level, code = geoids.parse(geoid)

        assert level == 'country-subset'
        assert code == 'country:code'

    def test_parse_invalid_geoid(self):
        geoid = 'this-is-not-a-geoid'

        with pytest.raises(geoids.GeoIDError):
            geoids.parse(geoid)

    def test_build(self):
        level = 'level'
        code = 'code'

        geoid = geoids.build(level, code)

        assert geoid == 'level:code'

    def test_from_zone(self):
        level = 'level'
        code = 'code'
        zone = GeoZone(level=level, code=code)

        geoid = geoids.from_zone(zone)

        assert geoid == 'level:code'
