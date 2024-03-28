import logging
import warnings

from urllib.parse import urlparse

from mongoengine.errors import ValidationError

from udata.mongo import db
from udata import entrypoints
from udata.errors import ConfigError

log = logging.getLogger(__name__)

class FieldValidationError(ValidationError):
    field: str

    def __init__(self, *args, field: str, **kwargs):
        self.field = field
        super().__init__(*args, **kwargs)

# Load all core models and mixins
from udata.core.spatial.models import *  # noqa
from udata.core.metrics.models import *  # noqa
from udata.core.badges.models import *  # noqa
from udata.core.discussions.models import *  # noqa
from udata.core.followers.models import *  # noqa
from udata.core.user.models import *  # noqa
from udata.core.organization.models import *  # noqa
from udata.core.contact_point.models import *  # noqa
from udata.core.site.models import *  # noqa
from udata.core.dataset.models import *  # noqa
from udata.core.reuse.models import *  # noqa
from udata.core.activity.models import *  # noqa
from udata.core.topic.models import *  # noqa
from udata.core.post.models import *  # noqa
from udata.core.jobs.models import *  # noqa
from udata.core.tags.models import *  # noqa
from udata.core.spam.models import *  # noqa

from udata.features.transfer.models import *  # noqa
from udata.features.territories.models import *  # noqa

# Load HarvestSource model as harvest for catalog
from udata.harvest.models import HarvestSource as Harvest  # noqa

import udata.linkchecker.models  # noqa


MONGODB_DEPRECATED_SETTINGS = 'MONGODB_PORT', 'MONGODB_DB'
MONGODB_DEPRECATED_MSG = '{0} is deprecated, use the MONGODB_HOST url syntax'



def validate_config(config):
    for setting in MONGODB_DEPRECATED_SETTINGS:
        if setting in config:
            msg = MONGODB_DEPRECATED_MSG.format(setting)
            log.warning(msg)
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
    url = config['MONGODB_HOST']
    parsed_url = urlparse(url)
    if not all((parsed_url.scheme, parsed_url.netloc)):
        raise ConfigError('{0} is not a valid MongoDB URL'.format(url))
    if len(parsed_url.path) <= 1:
        raise ConfigError('{0} is missing the database path'.format(url))


def build_test_config(config):
    if 'MONGODB_HOST_TEST' in config:
        config['MONGODB_HOST'] = config['MONGODB_HOST_TEST']
    else:
        # use `{database_name}-test` database for testing
        parsed_url = urlparse(config['MONGODB_HOST'])
        parsed_url = parsed_url._replace(path='%s-test' % parsed_url.path)
        config['MONGODB_HOST'] = parsed_url.geturl()
    validate_config(config)


# Avoid nose misdetecting this function as a test
build_test_config.__test__ = False


def init_app(app):
    validate_config(app.config)
    if app.config['TESTING']:
        build_test_config(app.config)
    db.init_app(app)
    entrypoints.get_enabled('udata.models', app)
