"""
This module centralize GeoID resources and helpers.

See https://github.com/etalab/geoids for more details
"""

__all__ = ("GeoIDError", "build", "from_zone", "parse")


class GeoIDError(ValueError):
    """Raised when an error occur while parsing or building a GeoID"""


def parse(text):
    """Parse a geoid from text and return a tuple (level, code, validity)"""
    # Kept validity parsing for legacy parsing and migration.
    # Validity is parsed but ignored.
    if "@" in text:
        spatial, _validity = text.split("@")
    else:
        spatial = text
    spatial = spatial.lower().replace("/", ":")  # Backward compatibility
    if ":" not in spatial:
        raise GeoIDError(f"Bad GeoID format: {text}")
    # country-subset is a special case:
    if spatial.startswith("country-subset:"):
        level, code = spatial.split(":", 1)
    else:
        level, code = spatial.rsplit(":", 1)
    return level, code


def build(level, code):
    """Serialize a GeoID from its parts"""
    return f"{level}:{code}"


def from_zone(zone):
    """Build a GeoID from a given zone"""
    return build(zone.level, zone.code)
