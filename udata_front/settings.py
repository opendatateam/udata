"""
Default settings for udata-front
"""

# TODO: move this back to an extension
RESOURCES_SCHEMAGOUVFR_ENABLED = True
SCHEMA_GOUVFR_VALIDATA_URL = 'https://validata.etalab.studio'
SCHEMA_CATALOG_URL = 'https://schema.data.gouv.fr/schemas/schemas.json'

# Dataset settings
# Default page size for resources on dataset page
RESOURCES_DEFAULT_PAGE_SIZE = 6

# Frontend banner parameters
BANNER_ACTIVATED = False
BANNER_HTML_CONTENT_EN = ''
BANNER_HTML_CONTENT_FR = ''

# Static pages from github repo
PAGES_GH_REPO_NAME = 'etalab/datagouvfr-pages'
PAGES_REPO_BRANCH = 'master'

# api.gouv.fr
APIGOUVFR_URL = 'https://api.gouv.fr/api/v1/apis'
APIGOUVFR_ALLOW_OPENNESS = ['open', 'semi_open']

# Etalab Guides
ETALAB_GUIDES_URL = 'https://guides.etalab.gouv.fr'
GUIDES_USER_ACCOUNT_URL = 'https://guides.etalab.gouv.fr/data.gouv.fr/creer-compte-utilisateur/'
GUIDES_ORGANIZATION_URL = 'https://guides.etalab.gouv.fr/data.gouv.fr/creer-rejoindre-organisation/'
GUIDES_DATASET_URL = 'https://guides.etalab.gouv.fr/data.gouv.fr/publier-jeu-de-donnees/'
GUIDES_REUSE_URL = 'https://guides.etalab.gouv.fr/reutilisation/publier-reutilisation/'
