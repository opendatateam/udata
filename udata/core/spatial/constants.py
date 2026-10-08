from udata.i18n import L_

BASE_GRANULARITIES = [
    ("poi", L_("POI")),
    ("other", L_("Other")),
]

ADMIN_LEVEL_MIN = 1
ADMIN_LEVEL_MAX = 110

# Dataset extras key holding the zone ids detected from `spatial.geom`
DETECTED_ZONES_KEY = "analysis:spatial:zones"
