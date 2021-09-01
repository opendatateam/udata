import copy
import pytest

from flask import current_app

from udata.core.dataset.factories import DatasetFactory
from udata_front import APIGOUVFR_EXTRAS_KEY
from udata_front.tests import GouvFrSettings
from udata_front.tasks import apigouvfr_load_apis


@pytest.mark.usefixtures('clean_db')
class ApiGouvFrTasksTest:
    settings = GouvFrSettings
    modules = []

    def test_apigouvfr_load_apis(app, rmock):
        dataset = DatasetFactory()
        url = current_app.config.get('APIGOUVFR_URL')
        apis = [{
            'title': 'une API',
            'tagline': 'tagline',
            'path': '/path',
            'slug': 'slug',
            'owner': 'owner',
            'openness': 'open',
            'logo': '/logo.png',
        }]
        payload = copy.deepcopy(apis)
        payload[0]['datagouv_uuid'] = [str(dataset.id), 'nope']
        # missing fields, won't be processed
        payload.append({
            'title': 'une autre API',
            'datagouv_uuid': [str(dataset.id)],
        })
        rmock.get(url, json=payload)
        apigouvfr_load_apis()
        dataset.reload()
        assert dataset.extras.get(APIGOUVFR_EXTRAS_KEY) == apis
