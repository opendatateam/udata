import logging
import warnings
from urllib.parse import urlparse

from udata.errors import ConfigError

from .engine import db

log = logging.getLogger(__name__)

MONGODB_DEPRECATED_SETTINGS = "MONGODB_PORT", "MONGODB_DB"
MONGODB_DEPRECATED_MSG = "{0} is deprecated, use the MONGODB_HOST url syntax"


def validate_config(config):
    for setting in MONGODB_DEPRECATED_SETTINGS:
        if setting in config:
            msg = MONGODB_DEPRECATED_MSG.format(setting)
            log.warning(msg)
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
    url = config["MONGODB_HOST"]
    parsed_url = urlparse(url)
    if not all((parsed_url.scheme, parsed_url.netloc)):
        raise ConfigError("{0} is not a valid MongoDB URL".format(url))
    if len(parsed_url.path) <= 1:
        raise ConfigError("{0} is missing the database path".format(url))


def build_test_config(config):
    if "MONGODB_HOST_TEST" in config:
        config["MONGODB_HOST"] = config["MONGODB_HOST_TEST"]
    else:
        # use `{database_name}-test` database for testing
        parsed_url = urlparse(config["MONGODB_HOST"])
        parsed_url = parsed_url._replace(path="%s-test" % parsed_url.path)
        config["MONGODB_HOST"] = parsed_url.geturl()
    validate_config(config)


def init_app(app):
    validate_config(app.config)
    if app.config["TESTING"]:
        build_test_config(app.config)
    db.init_app(app)
