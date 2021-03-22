"""
Default settings for udata-gouvfr
"""

# Frontend banner parameters
BANNER_ACTIVATED = False
BANNER_HTML_CONTENT = ''

# Static pages from github repo
PAGES_GH_REPO_NAME = 'etalab/datagouvfr-pages'
PAGES_REPO_BRANCH = 'master'

# api.gouv.fr
APIGOUVFR_URL = 'https://api.gouv.fr/api/v1/apis'
APIGOUVFR_ALLOW_OPENNESS = ['open', 'semi_open']

# Newsletter's subscription page's link
POST_BANNER_ACTIVATED = True
POST_BANNER_LINK = 'https://infolettres.etalab.gouv.fr/subscribe/rn7y93le1'
POST_BANNER_MESSAGE = 'Pour ne rien manquer, de l’actualité de data.gouv.fr'\
                      'et de l’open data, inscrivez-vous à notre infolettre.'
