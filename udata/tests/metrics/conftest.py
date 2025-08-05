import pytest

from udata import settings
from udata.app import create_app


class MetricsSettings(settings.Testing):
    PLUGINS = ["metrics"]
    METRICS_API = "http://metrics-api.fr/api"


@pytest.fixture
def app():
    app = create_app(settings.Defaults, override=MetricsSettings)
    return app
