from udata.settings import Testing


class GouvFrSettings(Testing):
    TEST_WITH_THEME = True
    TEST_WITH_PLUGINS = True
    PLUGINS = ['front']
    THEME = 'gouvfr'
    WP_ATOM_URL = None  # Only activated on specific tests
