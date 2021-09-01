import mongoengine
import requests

from collections import defaultdict
from flask import current_app

from udata.commands import success, error
from udata.core.dataset.models import Dataset
from udata.tasks import job

from udata_front import (
    APIGOUVFR_EXTRAS_KEY,
    APIGOUVFR_EXPECTED_FIELDS,
)


def get_dataset(id_or_slug):
    obj = Dataset.objects(slug=id_or_slug).first()
    return obj or Dataset.objects.get(id=id_or_slug)


def process_dataset(d_id, apis):
    try:
        dataset = get_dataset(d_id)
    except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
        return error(f'Dataset {d_id} not found')
    dataset.extras[APIGOUVFR_EXTRAS_KEY] = apis
    dataset.save()
    success(f'Imported {len(apis)} API(s) for {str(dataset)}')


@job('apigouvfr-load-apis')
def apigouvfr_load_apis(self):
    '''Load dataset-related APIs from api.gouv.fr'''
    r = requests.get(current_app.config['APIGOUVFR_URL'], timeout=10)
    r.raise_for_status()

    # cleanup existing mappings
    Dataset.objects.filter(**{
        f'extras__{APIGOUVFR_EXTRAS_KEY}__exists': True,
    }).update(**{
        f'unset__extras__{APIGOUVFR_EXTRAS_KEY}': True,
    })

    apis = r.json()
    datasets_apis = defaultdict(list)
    for api in apis:
        d_ids = api.pop('datagouv_uuid', [])
        if not d_ids:
            continue
        if not all([k in api for k in APIGOUVFR_EXPECTED_FIELDS]):
            error(f'Missing field in payload: {api}')
            continue
        if api['openness'] not in current_app.config.get('APIGOUVFR_ALLOW_OPENNESS', []):
            continue
        for d_id in d_ids:
            if api not in datasets_apis[d_id]:
                datasets_apis[d_id].append(api)

    for d_id, d_apis in datasets_apis.items():
        process_dataset(d_id, d_apis)

    success('Done.')
